import json,subprocess
from scripts.verify_docker_local import OUT,CFG
from scripts.record_command import safe_env
p=subprocess.run(['E:/Development/Docker/App/resources/bin/docker.exe','--config',str(CFG),'--host','npipe:////./pipe/dockerDesktopLinuxEngine','info','--format','{{json .}}'],env=safe_env(),capture_output=True,text=True,timeout=20)
d=json.loads(p.stdout) if p.returncode==0 else {}
r={k:v for k,v in d.items() if any(x in k.lower() for x in ['memory','swap','pids','cfs','security','ostype'])}
(OUT/'docker_json_controls.json').write_text(json.dumps({'exit_code':p.returncode,'controls':r},indent=2),encoding='utf-8')
print(json.dumps(r))
