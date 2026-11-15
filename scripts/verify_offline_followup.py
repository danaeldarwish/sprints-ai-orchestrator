"""New evidence only: requested controls, complete offline tests, notebook, graph cases."""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,sys,json,time,os
from scripts.record_command import safe_env
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evidence'/'followup_20261115'/'verified_pid';OUT.mkdir(parents=True,exist_ok=True)
env=safe_env();env['SPRINTS_SANDBOX_IMAGE']=json.loads((OUT.parent/'sandbox_image.json').read_text())['image']['id']
def capture(name,args,timeout=600):
    t=time.perf_counter();p=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
    (OUT/(name+'.stdout.txt')).write_text(p.stdout,encoding='utf-8');(OUT/(name+'.stderr.txt')).write_text(p.stderr,encoding='utf-8')
    meta={'command':args,'at':datetime.now(timezone.utc).isoformat(),'exit_code':p.returncode,'duration_s':round(time.perf_counter()-t,3),'sandbox_image':env['SPRINTS_SANDBOX_IMAGE'],'llm':'offline','credentials':'not loaded'}
    (OUT/(name+'.json')).write_text(json.dumps(meta,indent=2),encoding='utf-8');print(json.dumps(meta),p.stdout[-5000:],p.stderr[-1500:],flush=True)
    return p.returncode
steps=[('effective_controls',[sys.executable,'-m','scripts.verify_sandbox_controls']),('full_tests',[sys.executable,'-m','pytest','-q','-rs','-p','no:cacheprovider','--log-file='+str(OUT/'runtime.log'),'--log-file-level=INFO','--junitxml='+str(OUT/'full_tests.xml')]),('verified_notebook',[sys.executable,'-m','scripts.execute_verified_notebook']),('real_graph_scenarios',[sys.executable,'scripts/evaluate_followup.py']),('dependency_check',[sys.executable,'-m','pip','check'])]
for name,args in steps:
    code=capture(name,args)
    if code:raise SystemExit(code)
prefix=['E:/Development/Docker/App/resources/bin/docker.exe','--config',str(OUT/'docker-config'),'--host','npipe:////./pipe/dockerDesktopLinuxEngine']
raise SystemExit(capture('cleanup_final',prefix+['ps','--all','--filter','name=sprints-submission-','--format','{{json .}}']))
