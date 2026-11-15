"""Static policy, mocked Docker transport, and separately marked real containment."""
import io
import json
from types import SimpleNamespace
import pytest
from src.tools import code_repl as m
run=m.run_python_sandboxed

@pytest.mark.parametrize("code",[
"import os\nprint(os.listdir('/'))","import subprocess","import socket","from os import path",
"print(open('/etc/passwd').read())","print(eval('1+1'))","exec('print(1)')",
"print(().__class__.__bases__[0].__subclasses__())","print(getattr(int,'real'))",
"print('{0.__class__}'.format(1))","__import__('os')","print(globals())"])
def test_static_attack_screening_only(code,monkeypatch):
    monkeypatch.setattr(m,"_execute_container",lambda *a: pytest.fail("blocked code reached executor"))
    out=run(code)
    assert out.status=="blocked" and out.violations and out.stdout==""

def test_syntax_error_never_starts_execution(monkeypatch):
    monkeypatch.setattr(m,"_execute_container",lambda *a: pytest.fail("syntax error executed"))
    assert run("def f(:").status=="syntax_error"

def test_missing_sandbox_never_uses_host_python(monkeypatch):
    import subprocess,sys
    guard=subprocess.run([sys.executable,str(m._RUNNER)],input="",capture_output=True,text=True,timeout=5)
    assert guard.returncode!=0 and "Container-only runner" in guard.stderr
    monkeypatch.setattr(m,"sandbox_capabilities",lambda:{"available":False,"reason":"fixture unavailable"})
    monkeypatch.setattr(m.subprocess,"Popen",lambda *a,**k:pytest.fail("host subprocess fallback"))
    out=run("print(45)")
    assert out.status=="unable_to_verify" and out.exit_code is None
    assert json.loads(m.execute_python.invoke({"code":"print(2)"}))["status"]=="unable_to_verify"

def test_cli_env_omits_credentials_and_remote_endpoints(monkeypatch):
    for name in ("OPENAI_API_KEY","AWS_SECRET_ACCESS_KEY","DOCKER_HOST","DOCKER_CONTEXT","HTTP_PROXY"):
        monkeypatch.setenv(name,"TEST-SENTINEL-NOT-A-SECRET")
    assert all(n not in m._cli_env() for n in ("OPENAI_API_KEY","AWS_SECRET_ACCESS_KEY","DOCKER_HOST","DOCKER_CONTEXT","HTTP_PROXY"))

def test_container_policy_is_restricted_and_has_no_mounts():
    args=m._container_args("sha256:"+"a"*64,"fixed-test","trusted-bootstrap",5)
    for key,value in {"--network":"none","--user":"65534:65534","--cap-drop":"ALL","--security-opt":"no-new-privileges:true","--memory":"512m","--memory-swap":"512m","--cpus":"0.5","--pids-limit":"32","--pull":"never"}.items():
        assert args[args.index(key)+1]==value
    assert "--read-only" in args and "--init" in args
    assert not any(x in args for x in ("--privileged","--mount","--volume","-v","--device"))

class FakeProcess:
    def __init__(self,out=b"45\n",err=b""):
        self.stdin=io.BytesIO(); self.stdout=io.BytesIO(b"SPRINTS_READY_V1\n"+out); self.stderr=io.BytesIO(err)
        self.returncode=0
    def poll(self): return self.returncode
    def wait(self,timeout=None): return self.returncode
    def kill(self): self.returncode=-9

@pytest.mark.parametrize("mode",["ok","nonzero","oom","create_error","inspect_error","cleanup_error","stdout_flood","stderr_flood"])
def test_mock_transport_capture_and_cleanup(monkeypatch,mode):
    calls=[]
    monkeypatch.setattr(m,"sandbox_capabilities",lambda:{"available":True,"image":"sha256:"+"a"*64})
    monkeypatch.setattr(m,"_docker_prefix",lambda cfg:["docker","--config",cfg,"--host","local-fixture"])
    def control(prefix,args,timeout=8):
        calls.append(args)
        if args[0]=="create": return SimpleNamespace(returncode=int(mode=="create_error"),stdout="")
        if args[0]=="inspect":
            return SimpleNamespace(returncode=int(mode=="inspect_error"),stdout=json.dumps({"Running":False,"ExitCode":1 if mode=="nonzero" else 0,"OOMKilled":mode=="oom"}))
        return SimpleNamespace(returncode=int(mode=="cleanup_error"),stdout="")
    monkeypatch.setattr(m,"_control",control)
    out=b"x"*20000 if mode=="stdout_flood" else b"45\n"
    err=b"x"*20000 if mode=="stderr_flood" else b""
    monkeypatch.setattr(m.subprocess,"Popen",lambda *a,**k:FakeProcess(out,err))
    result=m._execute_container("{}",1)
    assert any(a[0]=="rm" and "--force" in a for a in calls)
    assert len(result.stdout)<=4000 and len(result.stderr)<=4000
    expected={"ok":"ok","nonzero":"runtime_error","oom":"runtime_error","create_error":"unable_to_verify","inspect_error":"unable_to_verify","cleanup_error":"unable_to_verify","stdout_flood":"output_limit","stderr_flood":"output_limit"}
    assert result.status==expected[mode]

@pytest.mark.parametrize("code,expected",[
("print(sum(range(10)))","ok"),("x=1\nprint(1/0)","runtime_error"),
("while True: pass","timeout"),("x=[0]*(10**10)","runtime_error"),
("while True: print('a'*1000)","output_limit"),
("import math\nprint(math.sqrt(16))","ok"),
])
@pytest.mark.sandbox_integration
def test_actual_isolated_execution(container,code,expected):
    result=run(code,timeout_s=2 if expected=="timeout" else 5)
    assert result.status==expected and result.exit_code is not None
    assert len(result.stdout)<=4000 and len(result.stderr)<=4000

@pytest.mark.parametrize("code,expected",[
("import os\nprint(os.getuid())","65534"),
("import os\nprint(os.path.exists('/workspace'))\nprint(os.path.exists('/host'))","False"),
("import os\nprint(os.environ.get('OPENAI_API_KEY','ABSENT'))","ABSENT"),
("import os\ntry:\n    os.mkdir('/escape')\nexcept OSError:\n    print('READ_ONLY')","READ_ONLY"),
("import subprocess\nprint(subprocess.run(['python','-I','-S','-c','import os;print(os.getuid())'],capture_output=True,text=True).stdout.strip())","65534"),
("import os\nprint(os.path.exists('/proc/1/root/host'))","False"),
("import os\ndef cg(name):\n    fd=os.open('/sys/fs/cgroup/'+name,os.O_RDONLY)\n    try:\n        return os.read(fd,4096).decode().strip()\n    finally:\n        os.close(fd)\ndef events():\n    return {line.split()[0]:int(line.split()[1]) for line in cg('pids.events').splitlines()}['max']\nassert cg('pids.max')=='32'\nbefore=events()\nchildren=[]\nr,w=os.pipe()\nlimited=False\nat_limit=0\ntry:\n    for i in range(64):\n        pid=os.fork()\n        if pid==0:\n            os.close(w)\n            os.read(r,1)\n            os._exit(0)\n        children.append(pid)\nexcept OSError as exc:\n    if exc.errno!=11:\n        raise\n    limited=True\n    at_limit=int(cg('pids.current'))\nfinally:\n    for pid in children:\n        try:\n            os.kill(pid,15)\n        except OSError:\n            pass\n    for pid in children:\n        os.waitpid(pid,0)\n    os.close(r)\n    os.close(w)\nafter=events()\nassert limited and at_limit==32 and after>before\nprint('PROCESS_LIMIT',len(children),'pids.max=32','events_delta='+str(after-before))","PROCESS_LIMIT"),
("import socket\ns=socket.socket()\ns.settimeout(.2)\ntry:\n    s.connect(('1.1.1.1',443))\nexcept OSError:\n    print('NO_NETWORK')","NO_NETWORK"),
])
@pytest.mark.sandbox_integration
def test_actual_kernel_boundary_independent_of_ast(container,code,expected):
    payload=json.dumps({"code":code,"harness":"","allowed_modules":["os","socket","subprocess"],"max_output_chars":4000})
    out=m._execute_container(payload,5)
    assert out.status=="ok" and expected in out.stdout


def test_mock_wall_timeout_kills_and_removes_container(monkeypatch):
    proc=FakeProcess();proc.returncode=None;calls=[]
    monkeypatch.setattr(m,"sandbox_capabilities",lambda:{"available":True,"image":"sha256:"+"a"*64})
    monkeypatch.setattr(m,"_docker_prefix",lambda cfg:["docker-fixture"])
    monkeypatch.setattr(m.subprocess,"Popen",lambda *a,**k:proc)
    clock=iter([0,10]);monkeypatch.setattr(m.time,"monotonic",lambda:next(clock))
    def control(prefix,args,timeout=8):
        calls.append(args[0])
        if args[0]=="kill":proc.returncode=137
        if args[0]=="inspect":return SimpleNamespace(returncode=0,stdout=json.dumps({"Running":False,"ExitCode":137,"OOMKilled":False}))
        return SimpleNamespace(returncode=0,stdout="")
    monkeypatch.setattr(m,"_control",control)
    result=m._execute_container("{}",1)
    assert result.status=="timeout" and result.exit_code==137
    assert "kill" in calls and "rm" in calls


def test_oversized_wire_is_rejected_before_docker(monkeypatch):
    calls=[]
    monkeypatch.setattr(m,'sandbox_capabilities',lambda:calls.append(1) or {'available':False,'reason':'fixture'})
    assert m._execute_container(' '*(512*1024-1),5).status=='unable_to_verify'
    assert len(calls)==1
    assert 'frame too large' in m._execute_container(' '*(512*1024),5).stderr
    assert 'frame too large' in m._execute_container('é'*(256*1024),5).stderr
    assert len(calls)==1

def test_runner_protocol_failure_is_infrastructure_failure(monkeypatch):
    monkeypatch.setattr(m,'sandbox_capabilities',lambda:{'available':True,'image':'sha256:'+'a'*64})
    monkeypatch.setattr(m,'_docker_prefix',lambda cfg:['local-fixture'])
    def control(prefix,args,timeout=8):
        return SimpleNamespace(returncode=0,stdout=json.dumps({'Running':False,'ExitCode':64,'OOMKilled':False}) if args[0]=='inspect' else '')
    monkeypatch.setattr(m,'_control',control)
    monkeypatch.setattr(m.subprocess,'Popen',lambda *a,**k:FakeProcess())
    assert m._execute_container('{}',5).status=='unable_to_verify'

@pytest.mark.sandbox_integration
def test_actual_runner_produces_output_before_stdin_eof(container):
    import subprocess,tempfile,threading,secrets
    with tempfile.TemporaryDirectory(prefix='sprints-framing-') as cfg:
        prefix=m._docker_prefix(cfg);name='sprints-submission-'+secrets.token_hex(12);proc=None
        try:
            made=m._control(prefix,m._container_args(container['image'],name,m._runner_bootstrap(),5))
            assert made.returncode==0
            proc=subprocess.Popen([*prefix,'start','--attach','--interactive',name],env=m._cli_env(),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            payload=json.dumps({'code':"print('FRAME_OK مرحبا')\nprint(2+2)",'harness':'','allowed_modules':[],'max_output_chars':4000},ensure_ascii=False).encode('utf-8')+b'\n'
            output=[];event=threading.Event();ready=threading.Event()
            def read():
                if proc.stdout.readline(128)==b'SPRINTS_READY_V1\n':ready.set()
                output.append(proc.stdout.readline(512).decode('utf-8'));event.set()
            reader=threading.Thread(target=read,daemon=True);reader.start()
            assert ready.wait(8),'Trusted startup did not complete'
            proc.stdin.write(payload);proc.stdin.flush()
            assert event.wait(5),'Runner waited for EOF despite a complete frame'
            assert not proc.stdin.closed and output[0]=='FRAME_OK مرحبا\n'
            proc.stdin.close();proc.wait(timeout=3);reader.join(timeout=1)
            state=m._control(prefix,['inspect',name,'--format','{{json .State}}'])
            assert state.returncode==0 and json.loads(state.stdout)['ExitCode']==0
        finally:
            if proc and proc.poll() is None:proc.kill();proc.wait(timeout=3)
            removed=m._control(prefix,['rm','--force',name]);assert removed.returncode==0

@pytest.mark.sandbox_integration
def test_actual_raw_stderr_limit(container):
    payload=json.dumps({'code':"import os\nwhile True:\n    os.write(2,b'x'*1000)",'harness':'','allowed_modules':['os'],'max_output_chars':4000})
    out=m._execute_container(payload,5)
    assert out.status=='output_limit' and len(out.stderr)<=4000


@pytest.mark.parametrize('started,finished,exit_code,status',[
('2026-11-15T00:00:00Z','2026-11-15T00:00:01Z',0,'ok'),
('2026-11-15T00:00:00Z','2026-11-15T00:00:01Z',137,'timeout'),
('2026-11-15T00:00:00Z','2026-11-15T00:00:10Z',0,'timeout'),
('2026-11-15T00:00:01Z','2026-11-15T00:00:00Z',0,'timeout'),
(None,None,0,'timeout')])
def test_delayed_attach_requires_authoritative_in_budget_exit(monkeypatch,started,finished,exit_code,status):
    proc=FakeProcess();proc.returncode=None
    monkeypatch.setattr(m,'sandbox_capabilities',lambda:{'available':True,'image':'sha256:'+'a'*64})
    monkeypatch.setattr(m,'_docker_prefix',lambda cfg:['local-fixture'])
    monkeypatch.setattr(m.subprocess,'Popen',lambda *a,**k:proc)
    clock=iter([0,10]);monkeypatch.setattr(m.time,'monotonic',lambda:next(clock))
    def control(prefix,args,timeout=8):
        if args[0]=='kill':proc.returncode=137
        state={'Status':'exited','Running':False,'ExitCode':exit_code,'OOMKilled':False,'StartedAt':started,'FinishedAt':finished}
        return SimpleNamespace(returncode=0,stdout=json.dumps(state) if args[0]=='inspect' else '')
    monkeypatch.setattr(m,'_control',control)
    result=m._execute_container('{}',5)
    assert result.status==status
    assert bool(result.transport_note)==(status=='ok')


@pytest.mark.parametrize('text',['','ordinary output','fixture:not-json','fixture:[]','fixture:[{"ok":"yes","input":"x","expected":"y","got":"z"}]'])
def test_missing_or_malformed_grading_verdict_is_unverifiable(monkeypatch,text):
    from src.rubric import ASSIGNMENTS
    assignment=next(v for v in ASSIGNMENTS.values() if v['kind']=='function')
    monkeypatch.setattr(m.secrets,'token_hex',lambda *a:'fixture')
    monkeypatch.setattr(m,'run_python_sandboxed',lambda *a:m.ReplResult('ok',stdout=text))
    result=m.run_with_tests('trusted fixture only',assignment)
    assert result['run']['status']=='unable_to_verify' and not result['tests']
