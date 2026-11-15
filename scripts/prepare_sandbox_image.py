"""Prepare a dedicated grading image from the public official Python base, no credentials."""
from pathlib import Path
import json,subprocess,sys,time
from scripts.record_command import safe_env
from scripts.verify_docker_local import run,CFG,OUT
DOCKER='E:/Development/Docker/App/resources/bin/docker.exe'
P=[DOCKER,'--config',str(CFG),'--host','npipe:////./pipe/dockerDesktopLinuxEngine']
def checked(name,args,timeout=240):
    began=time.perf_counter()
    p=subprocess.run(P+args,env=safe_env(),capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
    for suffix,value in [('stdout.txt',p.stdout),('stderr.txt',p.stderr)]: (OUT/(name+'.'+suffix)).write_text(value,encoding='utf-8')
    (OUT/(name+'.json')).write_text(json.dumps({'command':P+args,'exit_code':p.returncode,'duration_s':round(time.perf_counter()-began,3)},indent=2),encoding='utf-8')
    print(name,p.returncode,flush=True)
    if p.returncode: print(p.stderr[-3000:]);raise SystemExit(p.returncode)
    return p.stdout.strip()
base='python@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90'
checked('sandbox_base_pull',['pull',base])
meta=json.loads(checked('sandbox_base_inspect',['image','inspect',base,'--format','{"id":{{json .Id}},"digests":{{json .RepoDigests}},"os":{{json .Os}},"arch":{{json .Architecture}}}']))
pinned=next(d for d in meta['digests'] if d.startswith('python@sha256:'))
checked('sandbox_image_build',['build','--network','none','--pull=false','--build-arg','PYTHON_BASE='+pinned,'--tag','sprints-grading-sandbox:verified','--file','sandbox/Dockerfile','sandbox'])
image=json.loads(checked('sandbox_image_inspect',['image','inspect','sprints-grading-sandbox:verified','--format','{"id":{{json .Id}},"os":{{json .Os}},"arch":{{json .Architecture}},"user":{{json .Config.User}},"entrypoint":{{json .Config.Entrypoint}},"volumes":{{json (index .Config "Volumes")}}}']))
if image['os']!='linux' or image['user']!='65534:65534' or image['volumes']: raise SystemExit('Unexpected sandbox image configuration')
(OUT/'sandbox_image.json').write_text(json.dumps({'base':meta,'pinned_base':pinned,'image':image,'scope':'Dedicated minimal image; runtime uses immutable image ID, never pulls.'},indent=2),encoding='utf-8')
print(json.dumps(image),flush=True)
