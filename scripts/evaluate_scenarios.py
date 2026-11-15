"""Genuine offline application runs; review transitions are automated API fixtures.

The normal demo never approves tier-1. This separate regression harness uses a
trusted mock reviewer to exercise approve/reject authorization, not a real human.
"""
from pathlib import Path
import sys,os,tempfile,json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def main(directory):
    os.environ.update(SPRINTS_LLM="offline",SPRINTS_EMBEDDINGS="hashing",SPRINTS_LIVE_AUTHORIZED="0",
                      SPRINTS_CHROMA_DIR=str(Path(directory)/"chroma"),SPRINTS_DB_PATH=str(Path(directory)/"learners.db"),
                      ANONYMIZED_TELEMETRY="False",LANGSMITH_TRACING="false",LANGCHAIN_TRACING_V2="false")
    from src.tools.db_queries import build_database,get_learner_profile
    from src.tools.rag_retriever import ingest_curriculum
    from src.tools.code_repl import sandbox_capabilities
    from src.auth import MockIdentityProvider,AuthorizationError
    from src.service import OrchestratorService
    from src.main import BUGGY,FIXED
    from pydantic import ValidationError
    build_database(); ingest_curriculum()
    ids=MockIdentityProvider(); app=OrchestratorService(ids,warm=False)
    tokens={n:ids.issue_mock_session(f"learner-{n}") for n in (1001,1003,1005,1013,1018)}
    reviewer=ids.issue_mock_session("career-reviewer")
    records=[]
    for scenario,n,text in [
        ("1_curriculum",1001,"How do I make my agent remember each student?"),
        ("2_buggy_code",1005,BUGGY),("3_corrected_code",1005,FIXED),
        ("4_sqlite_matching",1003,"Which partner openings match me?"),
        ("5_tier1_pending_approve_fixture",1013,"Which partner openings match me?"),
        ("5_tier1_pending_reject_fixture",1018,"Which partner openings match me?"),
    ]:
        result=app.ask(tokens[n],{"text":text})
        record={"scenario":scenario,"evidence":"real local graph and tools; heuristic reasoner","result":result}
        if result["status"]=="pending_human_review":
            approve=n==1013
            decision={"pending_id":result["pending_id"],"approved":approve,"note":"Explicit automated reviewer API test fixture"}
            record["transition_fixture"]=app.review(reviewer,decision)
            assert ("Fawry" in record["transition_fixture"]["final_answer"])==approve
            try: app.review(reviewer,decision)
            except AuthorizationError: record["replay"]="denied"
            else: raise AssertionError("Replay was accepted")
        records.append(record)
    denials={}
    with ids.bind(tokens[1003]):
        denials["direct_other_profile"]=json.loads(get_learner_profile.invoke({"learner_id":"SPR-1001"}))["status"]
    try: app.ask(tokens[1003],{"text":"salary","thread_id":"learner-SPR-1001"})
    except ValidationError: denials["checkpoint_injection"]="denied"
    with ids.bind(tokens[1003]):
        assert json.loads(get_learner_profile.invoke({"learner_id":"SPR-1003"}))["learner_id"]=="SPR-1003"
    assert app.snapshot(tokens[1003])["turn_count"]==1
    records.append({"scenario":"6_learner_isolation","result":denials,"own_turn_count":app.snapshot(tokens[1003])["turn_count"]})
    result={"mode":"OFFLINE: no OpenAI requests; no credentials accessed","sandbox":sandbox_capabilities(),
            "scenarios":records,"review_audit":app.audit_events(reviewer)}
    output=ROOT/"evidence"/"evaluation";output.mkdir(parents=True,exist_ok=True)
    (output/"scenarios.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
if __name__=="__main__":
    if len(sys.argv)>1 and sys.argv[1]=="--worker":
        main(sys.argv[2])
    else:
        from scripts.record_command import safe_env
        with tempfile.TemporaryDirectory(prefix="sprints-e2e-") as directory:
            result=subprocess.run([sys.executable,str(Path(__file__).resolve()),"--worker",directory],env=safe_env())
            if result.returncode: raise SystemExit(result.returncode)
        print("Evaluation temporary database/index cleanup: complete")
