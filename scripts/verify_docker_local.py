"""Read-only local Docker/WSL diagnostics; no registry authentication or pulls."""
from pathlib import Path
import subprocess,json,time,os,shutil
from datetime import datetime,timezone
from scripts.record_command import safe_env
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence'/'followup_20261115'
CFG=OUT/'docker-config'; CFG.mkdir(parents=True,exist_ok=True)
def run(name,args,utf16=False):
    began=time.perf_counter()
    try:
        p=subprocess.run(args,env=safe_env(),stdin=subprocess.DEVNULL,capture_output=True,timeout=30)
        enc='utf-16-le' if utf16 and b'\x00' in p.stdout[:100] else 'utf-8'
        stdout=p.stdout.decode(enc,'replace');stderr=p.stderr.decode('utf-8','replace');code=p.returncode
    except Exception as exc: stdout='';stderr=type(exc).__name__+': '+str(exc);code=124
    (OUT/(name+'.stdout.txt')).write_text(stdout,encoding='utf-8')
    (OUT/(name+'.stderr.txt')).write_text(stderr,encoding='utf-8')
    meta={'command':args,'at':datetime.now(timezone.utc).isoformat(),'exit_code':code,'duration_s':round(time.perf_counter()-began,3)}
    (OUT/(name+'.json')).write_text(json.dumps(meta,indent=2),encoding='utf-8')
    print(json.dumps({'name':name,**meta,'stdout':stdout,'stderr':stderr}))
    return code
if __name__=='__main__':
    docker=shutil.which('docker')
    prefix=[docker,'--config',str(CFG),'--host','npipe:////./pipe/dockerDesktopLinuxEngine']
    run('privileged_docker_version',prefix+['version','--format','{{json .}}'])
    fmt='{{json .OSType}} {{json .MemoryLimit}} {{json .SwapLimit}} {{json .PidsLimit}} {{json .CPUCfsQuota}} {{json .SecurityOptions}}'
    run('privileged_docker_controls',prefix+['info','--format',fmt])
    run('privileged_docker_images',prefix+['image','ls','--no-trunc','--format','{{json .}}'])
    run('privileged_current_context',[docker,'context','show'])
    run('privileged_wsl_status',['wsl.exe','--status'],True)
    run('privileged_wsl_distros',['wsl.exe','--list','--verbose'],True)
