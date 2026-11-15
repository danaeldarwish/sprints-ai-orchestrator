"""Run real containment tests only after validated local image inspection."""
from pathlib import Path
import json,subprocess,sys,time
from scripts.record_command import safe_env
from scripts.verify_docker_local import OUT,CFG
ROOT=Path(__file__).resolve().parents[1]
prefix=['E:/Development/Docker/App/resources/bin/docker.exe','--config',str(CFG),'--host','npipe:////./pipe/dockerDesktopLinuxEngine']
fmt='{"id":{{json .Id}},"os":{{json .Os}},"arch":{{json .Architecture}},"user":{{json .Config.User}},"entrypoint":{{json .Config.Entrypoint}},"volumes":{{json (index .Config "Volumes")}}}'
def capture(name,args,env,timeout=300):
    t=time.perf_counter();p=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
    (OUT/(name+'.stdout.txt')).write_text(p.stdout,encoding='utf-8');(OUT/(name+'.stderr.txt')).write_text(p.stderr,encoding='utf-8')
    (OUT/(name+'.json')).write_text(json.dumps({'command':args,'exit_code':p.returncode,'duration_s':round(time.perf_counter()-t,3)},indent=2),encoding='utf-8')
    print(name,p.returncode,p.stdout[-5000:],p.stderr[-2000:],flush=True);return p
label=sys.argv[1] if len(sys.argv)>1 else 'verified'
p=capture('sandbox_image_inspect_'+label,prefix+['image','inspect','sprints-grading-sandbox:verified','--format',fmt],safe_env())
if p.returncode:raise SystemExit(p.returncode)
meta=json.loads(p.stdout)
assert meta['os']=='linux' and meta['user']=='65534:65534' and not meta['volumes']
base=json.loads((OUT/'sandbox_base_inspect.stdout.txt').read_text(encoding='utf-8'))
(OUT/'sandbox_image.json').write_text(json.dumps({'base':base,'pinned_base':base['digests'][0],'image':meta},indent=2),encoding='utf-8')
env=safe_env();env['SPRINTS_SANDBOX_IMAGE']=meta['id']
p=capture('sandbox_integration_'+label,[sys.executable,'-m','pytest','tests/test_sandbox.py','-m','sandbox_integration','-vv','--junitxml='+str(OUT/('sandbox_integration_'+label+'.xml'))],env)
capture('sandbox_cleanup_after_'+label,prefix+['ps','--all','--filter','name=sprints-submission-','--format','{{json .}}'],safe_env())
raise SystemExit(p.returncode)
