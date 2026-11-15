"""Prepare five genuine inference cases offline; execution needs separate approval.

No key is read by --plan. Never invoke --execute as part of an offline audit.
"""
from pathlib import Path
import argparse,json,os,sys,tempfile,subprocess,importlib.metadata
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
MODEL='gpt-4o-mini-2024-07-18'
PLAN={'status':'PREPARED_NOT_EXECUTED','model':MODEL,'max_requests':24,'input_admission_tokens_per_request':4000,'output_tokens_per_request':500,'timeout_s':20,'sdk_retries':0,'parser_attempts':2,'parser_attempts_consume_shared_budget':True,'stop_on_any_provider_error':True,'estimated_max_token_cost_usd':0.0216,'proposed_spend_ceiling_usd':0.05,'pricing_input_per_million':0.15,'pricing_output_per_million':0.60,'pricing_recheck_required_before_execution':True,'credentials':'User provisions only SPRINTS_VERIFICATION_API_KEY after separate explicit approval. No dotenv, ambient OPENAI_API_KEY or unrelated projects.','embeddings':'Local hashing; no paid embeddings','cases':['Curriculum Q&A with actual Chroma sources','Buggy Python: actual Linux evidence + structured grade','Corrected Python: actual Linux evidence + bounded LLM judge/optimizer','Career matching from actual scoped SQLite rows','Fawry tier-1 remains pending LangGraph human review'],'nominal_requests_without_repairs':17,'completion_not_guaranteed_within_cap':True,'runtime_evidence':['UTC timestamps','model and SDK versions','case/result schema and status','retrieved source IDs','tool/protocol metadata','response/request IDs','token usage and finish reason','per-request latency','exception class and HTTP status','sandbox image ID','no keys, sessions, headers or raw private prompts'],'actual_paid_requests':0}
def worker(out,approval):
    from src.live_controls import RequestBudget,configure_run,CASE
    from src.tools.code_repl import sandbox_capabilities
    from src.tools.db_queries import build_database
    from src.tools.rag_retriever import ingest_curriculum
    from src.auth import MockIdentityProvider
    from src.service import OrchestratorService
    from src.main import BUGGY,FIXED
    capability=sandbox_capabilities()
    if not capability['available']:raise SystemExit('Sandbox unavailable; grading cases cannot be verified')
    build_database();ingest_curriculum()
    budget=RequestBudget(24);configure_run(budget)
    ids=MockIdentityProvider();app=OrchestratorService(ids)
    sessions={n:ids.issue_mock_session('learner-'+str(n)) for n in (1001,1003,1005,1013)}
    cases=[('curriculum',1001,'How is a Python assignment scored?','advisor_curriculum'),('buggy_grading',1005,BUGGY,'assessor'),('corrected_optimizer',1005,FIXED,'assessor'),('sqlite_career',1003,'Which partner openings match me?','advisor_career'),('tier1_pending',1013,'Which partner openings match me?','advisor_career')]
    results=[];stop=None
    try:
        for name,n,text,route in cases:
            budget.assert_active();token=CASE.set(name)
            try:
                result=app.ask(sessions[n],{'text':text})
                valid=result.get('route')==route and not result.get('fallback')
                if route=='assessor':valid=valid and bool(result.get('assessment')) and result.get('refinement_count',0)<=3
                if name=='tier1_pending':valid=valid and result.get('status')=='pending_human_review' and 'Fawry' not in result.get('final_answer','')
                if name=='curriculum':valid=valid and bool(result.get('sources'))
                results.append({'case':name,'verified':valid,'result':{k:v for k,v in result.items() if k!='pending_id'}})
            finally:CASE.reset(token)
            if budget.stopped:raise RuntimeError('Provider run stopped; later cases not attempted')
    except Exception as exc:stop=type(exc).__name__
    finally:
        versions={name:importlib.metadata.version(name) for name in ('openai','langchain-openai','langgraph','chromadb','pydantic')}
        receipt={'status':'COMPLETE' if len(results)==5 and all(x['verified'] for x in results) and not stop else 'PARTIAL_OR_FAILED','approval_reference':approval,'model':MODEL,'sdk_versions':versions,'sandbox':capability,'results':results,'requests':budget.records,'stopped_exception':stop,'actual_attempts':len(budget.records),'unexecuted_cases':[name for name,_,_,_ in cases if name not in {r['case'] for r in results}],'review':'Tier-1 remains pending; no automated human decision','decision_quality':'Reviewer must inspect feedback and source/SQL grounding; infrastructure completion alone does not certify answer quality.'}
        (out/'live_results.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        print(json.dumps({'status':receipt['status'],'actual_attempts':len(budget.records),'verified_cases':sum(x['verified'] for x in results)}))
    return 0 if receipt['status']=='COMPLETE' else 1
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',action='store_true');p.add_argument('--execute',action='store_true');p.add_argument('--approval-id');p.add_argument('--output',default='evidence/followup_20261115/openai_plan.json');p.add_argument('--worker',action='store_true');a=p.parse_args()
    if not a.execute:
        output=ROOT/a.output;output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(PLAN,indent=2),encoding='utf-8');print(json.dumps(PLAN,indent=2));return 0
    if os.getenv('SPRINTS_LIVE_AUTHORIZED')!='1' or not a.approval_id:raise SystemExit('Separate explicit approval and an approval reference are required; no credential read')
    if os.getenv('SPRINTS_OPENAI_MODEL')!=MODEL:raise SystemExit('Exact approved model required; no fallback')
    if a.worker:return worker(Path(a.output),a.approval_id)
    key=os.environ.get('SPRINTS_VERIFICATION_API_KEY')
    if not key:raise SystemExit('Provision the dedicated verification credential; never borrow another project key')
    out=Path(a.output).resolve()
    if out.exists():raise SystemExit('Choose a new evidence directory; existing evidence is preserved')
    out.mkdir(parents=True)
    from scripts.record_command import safe_env
    with tempfile.TemporaryDirectory(prefix='sprints-live-') as tmp:
        env=safe_env();env.update(SPRINTS_LLM='openai',SPRINTS_OPENAI_MODEL=MODEL,SPRINTS_LIVE_AUTHORIZED='1',SPRINTS_VERIFICATION_API_KEY=key,SPRINTS_CHROMA_DIR=str(Path(tmp)/'chroma'),SPRINTS_DB_PATH=str(Path(tmp)/'learners.db'))
        run=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--execute','--worker','--approval-id',a.approval_id,'--output',str(out)],cwd=ROOT,env=env,timeout=900)
    return run.returncode
if __name__=='__main__':raise SystemExit(main())
