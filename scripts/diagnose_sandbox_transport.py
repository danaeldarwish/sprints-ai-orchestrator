"""Trusted minimal probes only; same restricted transport, metadata-only timeline."""
import os,json,time
from pathlib import Path
from scripts.record_command import safe_env
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evidence'/'followup_20261115'
os.environ['SPRINTS_SANDBOX_IMAGE']=json.loads((OUT/'sandbox_image.json').read_text())['image']['id']
from src.tools import code_repl as m
original=m._control;timeline=[]
def control(prefix,args,timeout=8):
    t=time.perf_counter()
    if args[0]=='kill':
        p=original(prefix,['inspect',args[1],'--format','{{json .State}}'])
        timeline.append({'event':'state_at_deadline_trusted_probe','state':json.loads(p.stdout) if p.returncode==0 else None})
    p=original(prefix,args,timeout)
    row={'operation':args[0],'duration_ms':round((time.perf_counter()-t)*1000,2),'exit_code':p.returncode}
    if args[0]=='inspect' and p.returncode==0:row['state']=json.loads(p.stdout)
    timeline.append(row);return p
m._control=control
results=[]
for i,code in enumerate(['print(45)','x=1\nprint(1/0)',"import os\ntry:\n    os.mkdir('/escape')\nexcept Exception:\n    print('READ_ONLY')"]):
    timeline.clear();p=m._execute_container(json.dumps({'code':code,'harness':'','allowed_modules':['os'],'max_output_chars':4000}),5)
    results.append({'case':i,'result':p.to_dict(),'timeline':list(timeline)});print(json.dumps(results[-1]),flush=True)
(OUT/'sandbox_transport_diagnosis.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
