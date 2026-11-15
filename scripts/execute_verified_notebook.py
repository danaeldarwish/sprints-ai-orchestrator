"""Execute genuine container-backed evaluation into a NEW notebook artifact."""
from pathlib import Path
import os,sys,json,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from scripts.record_command import safe_env
OUT=ROOT/'evidence'/'followup_20261115'
os.environ['SPRINTS_SANDBOX_IMAGE']=json.loads((OUT/'sandbox_image.json').read_text())['image']['id']
notebook=nbformat.read(ROOT/'notebooks'/'sources'/'evaluator_optimizer_verified.ipynb',as_version=4)
with tempfile.TemporaryDirectory(prefix='sprints-verified-kernel-') as kernel:
    base=Path(kernel);spec=base/'sprints-audit';spec.mkdir()
    (spec/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','--HistoryManager.hist_file=:memory:','-f','{connection_file}'],'display_name':'Sprints verified sandbox','language':'python','env':safe_env()}),encoding='utf-8')
    manager=KernelManager(kernel_name='sprints-audit',kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(base)]),connection_file=str(base/'connection.json'))
    client=NotebookClient(notebook,km=manager,timeout=180,resources={'metadata':{'path':str(ROOT)}})
    env=safe_env();env.update(IPYTHONDIR=str(base/'ipython'),JUPYTER_CONFIG_DIR=str(base/'config'),JUPYTER_RUNTIME_DIR=str(base/'runtime'))
    try:client.execute(env=env)
    finally:manager.shutdown_kernel(now=True);manager.cleanup_resources()
nbformat.validate(notebook)
code=[c for c in notebook.cells if c.cell_type=='code'];assert all(c.execution_count is not None for c in code)
assert not any(o.output_type=='error' for c in code for o in c.outputs)
target=ROOT/'notebooks'/'evaluator_optimizer_verified.ipynb';nbformat.write(notebook,target)
receipt={'notebook':str(target.relative_to(ROOT)),'all_executed':True,'code_cells':len(code),'errors':0,'learner_execution':'actual restricted Linux Docker','reasoning':'offline deterministic; faulty grader injection explicitly labeled','image':os.environ['SPRINTS_SANDBOX_IMAGE']}
(OUT/'notebook_execution.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print(json.dumps(receipt))
