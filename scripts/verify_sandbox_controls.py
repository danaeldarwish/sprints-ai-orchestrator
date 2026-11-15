"""Inspect actual requested container controls and effective kernel state."""
import json,os,secrets,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'evidence'/'followup_20261115';OUT=BASE/'verified_pid';OUT.mkdir(parents=True,exist_ok=True)
os.environ['SPRINTS_SANDBOX_IMAGE']=json.loads((BASE/'sandbox_image.json').read_text())['image']['id']
from src.tools import code_repl as m
from scripts.verify_docker_local import CFG
prefix=m._docker_prefix(str(CFG));name='sprints-control-'+secrets.token_hex(12);image=os.environ['SPRINTS_SANDBOX_IMAGE']
receipt={'image':image}
try:
    created=m._control(prefix,m._container_args(image,name,'print(45)',5));assert created.returncode==0
    p=m._control(prefix,['inspect',name,'--format','{{json .}}']);assert p.returncode==0;d=json.loads(p.stdout);h=d['HostConfig']
    keys=['NetworkMode','ReadonlyRootfs','CapDrop','SecurityOpt','Memory','MemorySwap','NanoCpus','PidsLimit','Ulimits','Tmpfs','Init','Binds','Privileged','Devices','DeviceRequests','PidMode']
    receipt['host_config']={k:h.get(k) for k in keys};receipt['user']=d['Config']['User'];receipt['mounts']=d.get('Mounts',[]);receipt['stdin_config']={k:d['Config'].get(k) for k in ('OpenStdin','StdinOnce','AttachStdin')}
    assert receipt['user']=='65534:65534' and h['NetworkMode']=='none' and h['ReadonlyRootfs'] and h['CapDrop']==['ALL']
    assert h['Memory']==h['MemorySwap']==512*1024*1024 and h['NanoCpus']==500000000 and h['PidsLimit']==32
    assert any(x in h['SecurityOpt'] for x in ('no-new-privileges','no-new-privileges:true'))
    assert h['Init'] and not h['Privileged'] and not h.get('Binds') and not h.get('Devices') and not receipt['mounts']
    receipt['requested_controls_verified']=True
finally:
    clean=m._control(prefix,['rm','--force',name]);receipt['control_container_cleanup_exit']=clean.returncode
    (OUT/'sandbox_controls.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    assert clean.returncode==0
code="import os\nfd=os.open('/proc/self/status',os.O_RDONLY)\ns=os.read(fd,10000).decode()\nos.close(fd)\nfor line in s.splitlines():\n    if line.startswith(('Uid:','Gid:','CapEff:','NoNewPrivs:','Seccomp:')):\n        print(line)\nfor name in ('memory.max','memory.swap.max','pids.max','cpu.max'):\n    fd=os.open('/sys/fs/cgroup/'+name,os.O_RDONLY)\n    print(name,os.read(fd,1000).decode().strip())\n    os.close(fd)"
result=m._execute_container(json.dumps({'code':code,'harness':'','allowed_modules':['os'],'max_output_chars':4000}),5)
receipt['effective_kernel_probe']=result.to_dict()
(OUT/'sandbox_controls.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print(json.dumps(receipt,indent=2))
assert result.status=='ok' and 'NoNewPrivs:\t1' in result.stdout and 'Seccomp:\t2' in result.stdout and 'CapEff:\t0000000000000000' in result.stdout
