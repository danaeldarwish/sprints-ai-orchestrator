"""Rebuild and execute a trusted notebook; learner code uses the container only."""
from pathlib import Path
import os,sys,json,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from scripts.record_command import safe_env
def main():
    m=nbformat.v4.new_markdown_cell; c=nbformat.v4.new_code_cell
    cells=[
      m("# Assessor evaluation and optimization\n\nExecuted offline on 2026-11-15. Real LangGraph, Pydantic, SQLite and MemorySaver. Actual execution needs the verified Linux sandbox. The later optimizer examples use explicitly labeled known execution fixtures; they are not live learner-code execution or OpenAI inference."),
      c("from pathlib import Path\nimport os, tempfile, json\nworkspace = Path.cwd()\nif not (workspace/'src').exists(): workspace=workspace.parent\nimport sys\nsys.path.insert(0,str(workspace))\nrun_dir = tempfile.TemporaryDirectory(prefix='sprints-notebook-')\nos.environ.update(SPRINTS_LLM='offline', SPRINTS_EMBEDDINGS='hashing', SPRINTS_LIVE_AUTHORIZED='0', SPRINTS_CHROMA_DIR=str(Path(run_dir.name)/'chroma'), SPRINTS_DB_PATH=str(Path(run_dir.name)/'learners.db'), ANONYMIZED_TELEMETRY='False', LANGSMITH_TRACING='false', LANGCHAIN_TRACING_V2='false')\nfrom src.auth import MockIdentityProvider\nfrom src.service import OrchestratorService\nfrom src.main import BUGGY, FIXED\nfrom src.tools.code_repl import sandbox_capabilities\nprint(json.dumps(sandbox_capabilities(),indent=2))"),
      m("## Actual safe execution path\nThe application returns structured Unable to verify when containment is unavailable. No host fallback is permitted and no grade is invented."),
      c("identity=MockIdentityProvider()\napp=OrchestratorService(identity,warm=False)\nsession=identity.issue_mock_session('learner-1005')\nactual=[]\nfor submission in (BUGGY,FIXED):\n    result=app.ask(session,{'text':submission})\n    actual.append(result)\n    print(json.dumps(result,indent=2))\nif not sandbox_capabilities()['available']:\n    assert all(r['status']=='unable_to_verify' and not r.get('assessment') for r in actual)"),
      m("## Optimizer control flow using execution fixtures\nThese known fixture outcomes exercise feedback refinement and the three-refinement cap through the real graph. The fixture is never presented as measured Python execution. The judge here is deterministic, not an LLM."),
      c("from unittest.mock import patch\nfrom tests.test_evaluator_optimizer import execution_fixture, LearnsFromJudge, Inflater\nfixture_results=[]\nfor reasoner in (LearnsFromJudge(),Inflater()):\n    with patch('src.agents.assessor_agent.run_with_tests',execution_fixture):\n        fixture_app=OrchestratorService(identity,reasoner=reasoner,warm=False)\n        result=fixture_app.ask(session,{'text':BUGGY})\n    fixture_results.append(result)\n    print('MOCK_EXECUTION_FIXTURE',type(reasoner).__name__,json.dumps(result,indent=2))\nassert fixture_results[0]['refinement_count']==1\nassert fixture_results[1]['refinement_count']==3\nassert fixture_results[1]['grader_calls']==4\nassert fixture_results[1]['status']=='graded_needs_human_review'"),
      c("with patch('src.agents.assessor_agent.run_with_tests',execution_fixture):\n    corrected=OrchestratorService(identity,warm=False).ask(session,{'text':FIXED})\nprint('MOCK_EXECUTION_FIXTURE corrected',json.dumps(corrected,indent=2))\nassert corrected['assessment']['score']==100\nassert corrected['status']=='graded'"),
      m("## Interpretation\nThe notebook verifies typed grading output, bounded optimization, and safe degradation. Container containment and live OpenAI judgement remain unverified when unavailable. The 80% waiting-time reduction remains a stakeholder target; these timings do not measure business queue waiting.")
    ]
    notebook=nbformat.v4.new_notebook(cells=cells,metadata={"kernelspec":{"display_name":"Sprints isolated audit","language":"python","name":"sprints-audit"},"language_info":{"name":"python","version":sys.version.split()[0]}})
    target=ROOT/"notebooks"/"evaluator_optimizer_loop.ipynb"
    with tempfile.TemporaryDirectory(prefix="sprints-kernel-") as kernel:
        base=Path(kernel); spec=base/"sprints-audit";spec.mkdir()
        (spec/"kernel.json").write_text(json.dumps({"argv":[sys.executable,"-m","ipykernel_launcher","--HistoryManager.hist_file=:memory:","-f","{connection_file}"],"display_name":"Sprints isolated audit","language":"python","env":safe_env()}),encoding="utf-8")
        manager=KernelManager(kernel_name="sprints-audit",kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(base)]),connection_file=str(base/"connection.json"))
        client=NotebookClient(notebook,km=manager,timeout=120,resources={"metadata":{"path":str(ROOT)}})
        kernel_env=safe_env()
        kernel_env.update(IPYTHONDIR=str(base/"ipython"),JUPYTER_CONFIG_DIR=str(base/"config"),JUPYTER_RUNTIME_DIR=str(base/"runtime"))
        try:
            client.execute(env=kernel_env)
        finally:
            manager.shutdown_kernel(now=True)
            manager.cleanup_resources()
    nbformat.validate(notebook);nbformat.write(notebook,target)
    executed=[x for x in notebook.cells if x.cell_type=="code"]
    assert all(x.execution_count is not None for x in executed)
    assert not any(o.output_type=="error" for x in executed for o in x.outputs)
    print(json.dumps({"notebook":str(target.relative_to(ROOT)),"code_cells":len(executed),"all_executed":True,"errors":0}))
if __name__=="__main__":main()
