"""Build traceable requirement matrices from actual evidence, without inventing passes."""
from pathlib import Path
import json,sys,csv,hashlib,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
def reference(path,needle):
    for i,line in enumerate((ROOT/path).read_text(encoding="utf-8").splitlines(),1):
        if needle in line:return f"{path}:{i}"
    raise ValueError((path,needle))
def main():
    out=ROOT/"docs"/"audit";out.mkdir(parents=True,exist_ok=True)
    def row(i,name,base,final,code,evidence,limit=""):
        return {"id":i,"requirement":name,"baseline":base,"final":final,"code":code,"execution_evidence":evidence,"limits":limit}
    f=[
      row("F1","500-token Chroma ingestion, 50-token overlap","PARTIAL","PASS",reference("src/tools/rag_retriever.py","def chunk_documents"),"tests/test_rag.py; tests/test_security_regressions.py::test_exact_overlap_offsets_and_reencoded_token_sequences; evidence/benchmark/rag_latency.json","Actual Chroma, exact cl100k_base; embeddings are deterministic hashing."),
      row("F2","Pydantic score, feedback_points, pass_status","PARTIAL","PASS",reference("src/schemas.py","class AssessmentResult"),"tests/test_schemas_and_prompts.py; evidence/tests.xml","Schema/parser tests and mock execution fixtures; live model grading unverified."),
      row("F3","SQL learner progress, EGP target, employers","PARTIAL","PASS",reference("src/tools/db_queries.py","def get_learner_profile"),"tests/test_sql_tool.py; evidence/evaluation/scenarios.json","Actual SQLite rows; partner openings synthetic."),
      row("F4","Secure isolated Python execution","FAIL","PARTIAL",reference("src/tools/code_repl.py","def _execute_container"),"evidence/evaluation/scenarios.json; tests/test_sandbox.py; evidence/tests.xml","Host fallback removed. Linux Docker unavailable; 14 actual integration cases skipped. Kernel containment NOT VERIFIED."),
      row("F5","Unified TypedDict StateGraph, Advisor/Assessor routing","PARTIAL","PASS",reference("src/agents/orchestrator.py","def build_graph"),"tests/test_graph.py::test_routes_curriculum_career_grading; evidence/evaluation/scenarios.json","Real LangGraph execution with offline reasoning."),
      row("F6","MemorySaver and learner checkpoint isolation","PARTIAL","PASS",reference("src/service.py","class OrchestratorService"),"tests/test_graph.py::test_memory_and_public_snapshot_are_owned; tests/test_security_regressions.py","Mock authenticated application context only; process-local persistence."),
      row("F7","Agentic RAG critique, reformulation and retry","PARTIAL","PARTIAL",reference("src/agents/advisor_agent.py","def advisor_reflect"),"tests/test_graph.py::test_rag_reflects_and_reformulates; evidence/evaluation/scenarios.json","Actual retrieval and bounded control flow; critique is heuristic offline. Genuine live LLM reflection NOT VERIFIED."),
      row("F8","Assessor evaluator-optimizer with LLM-as-Judge","PARTIAL","PARTIAL",reference("src/agents/assessor_agent.py","def assessor_judge"),"tests/test_evaluator_optimizer.py; notebooks/evaluator_optimizer_loop.ipynb","Loop verified with declared execution fixtures and deterministic judge. Actual sandbox and live OpenAI judge NOT VERIFIED."),
      row("F9","Tier-1 LangGraph interrupt and explicit authorized review","FAIL","PASS",reference("src/service.py","def review("),"tests/test_graph.py; tests/test_security_regressions.py; evidence/evaluation/scenarios.json","Pending/approved/rejected transitions use mock reviewer sessions. Production identity and a real human recording remain unverified."),
      row("F10","HumanMessage, AIMessage, ToolMessage and trace logs","PARTIAL","PASS",reference("src/protocol.py","def tool_exchange"),"tests/test_graph.py::test_protocol_pairs_and_metadata_trace; evidence/commands/default_demo.stdout.txt","Metadata-only trace excludes records and tokens."),
    ]
    a=[
      row("A1","Use LangGraph orchestration","PARTIAL","PASS",reference("src/agents/orchestrator.py","StateGraph(OrchestratorState)"),"evidence/tests.xml; evidence/evaluation/scenarios.json"),
      row("A2","Detailed Sprints-specific docstrings","PASS","PASS","src/agents; src/tools; src/state.py; src/service.py","Source inspection; evidence/commands/syntax.json","Editorial review, not a claim that a style tool proved documentation quality."),
      row("A3","Chroma retrieval below 1000 ms","NOT VERIFIED","PARTIAL",reference("src/tools/rag_retriever.py","def retrieve("),"evidence/benchmark/rag_latency.json","Warm samples pass; cold samples may fail. Process startup is separately measured. No universal latency guarantee."),
      row("A4","SQL/Python failures return structured Unable to verify","PARTIAL","PASS","src/schemas.py:UnableToVerify; src/agents/assessor_agent.py:assessor_run","tests/test_sql_tool.py; tests/test_graph.py; evidence/evaluation/scenarios.json"),
      row("A5","At most three optimizer refinements","PARTIAL","PASS",reference("src/agents/assessor_agent.py","def route_after_judge"),"tests/test_evaluator_optimizer.py::test_hard_maximum_three_refinements; executed notebook","Real graph cap; mock execution evidence, deterministic judge."),
    ]
    d=[
      row("D1","Reproducible GitHub-ready repository","PARTIAL","PARTIAL","README.md; requirements.txt; requirements-lock.txt","evidence/commands/dependency_check.json; evidence/archive_verification.json","Offline reproduction only. No GitHub publication. Sandbox and paid inference require separate verification."),
      row("D2","Complete technical report PDF","FAIL","PASS","submission/technical_report.pdf","evidence/artifact_validation.json; evidence/render_review.md","Current limitations disclosed."),
      row("D3","8-10 slide presentation in PPTX and PDF","FAIL","PASS","submission/stakeholder_presentation.pptx; submission/stakeholder_presentation.pdf","evidence/artifact_validation.json; evidence/presentation_validation.json; evidence/render_review.md","10 slides; no original kickoff template available."),
      row("D4","Genuine 3-5 minute recorded demo","FAIL","FAIL","docs/demo_recording_script.md","No MP4 exists; duration NOT VERIFIED","Video PENDING. Exact 4:15 script is not a recorded video."),
      row("D5","Executed assessor evaluation notebook","PARTIAL","PARTIAL","notebooks/evaluator_optimizer_loop.ipynb","evidence/commands/notebook_execute.json","4 code cells executed, zero errors; actual sandbox path unavailable and optimization examples explicitly use fixtures."),
      row("D6","Final package and audit manifest","FAIL","PASS","submission/sprints-ai-orchestrator-final.zip; submission/audit_manifest.json","evidence/archive_verification.json","See final gate and source hashes."),
      row("D7","Supplied learner data and documented SQLite","PARTIAL","PASS","data/sprints_learner_db.csv; data/sprints_learner.db; docs/data_provenance.md","evidence/baseline/archive_manifest.json; evidence/quality_gate.json","25 learner records unchanged; 16 synthetic openings. No 500-record expansion."),
    ]
    s=[
      row("K1","Original kickoff PPTX content cross-check","NOT VERIFIED","NOT VERIFIED","_client_sources/README.md","User clarified original PPTX absent","Working notes cannot prove full deck fidelity."),
      row("K2","Kickoff mentions 500 learners","NOT VERIFIED","NOT VERIFIED","_client_sources/README.md; docs/data_provenance.md","25 CSV rows counted; original kickoff absent","500 remains an attributed independent finding, not independently verified media content."),
      row("K3","Original discovery MP3 and full transcript cross-check","NOT VERIFIED","NOT VERIFIED","_client_sources/client_discovery_call_transcript.md","User-supplied working summary only","Original MP3 and verbatim full transcript unavailable."),
      row("S1","80% waiting-time reduction target, honest measurement","PARTIAL","PASS","docs/business_metrics.md","No business event baseline; evaluation n=0","Target captured; achieved reduction NOT VERIFIED."),
      row("S2","Mandatory typed state and per-learner checkpoints","PARTIAL","PASS","src/state.py; src/service.py","evidence/tests.xml"),
      row("S3","Secure grading required by discovery","FAIL","PARTIAL","src/tools/code_repl.py","14 actual sandbox cases skipped","Containment unavailable; fail closed demonstrated."),
      row("S4","Prevent invented qualifications and wrong matches","PARTIAL","PASS","src/agents/advisor_agent.py:build_career_message; src/tools/db_queries.py:evaluate_openings","tests/test_graph.py::test_grounding_rejects_invented_partner_salary_opening; tests/test_sql_tool.py","Deterministic row-derived POC policy; real partner-policy validity unverified."),
      row("S5","Live Q&A, isolated grading and DB matching demo","PARTIAL","PARTIAL","src/main.py; docs/demo_recording_script.md","evidence/commands/default_demo.stdout.txt; evidence/evaluation/scenarios.json","Q&A and matching actual offline; grading unavailable, video pending, live LLM absent."),
    ]
    findings=[
      ("1","25 supplied records versus attributed kickoff 500","CONFIRMED 25; 500 NOT VERIFIED","CSV/hash check; original kickoff unavailable"),
      ("2","Locally generated SQLite, synthetic curriculum/openings","CONFIRMED","build_database seed rules; is_synthetic=1; synthetic Markdown labels"),
      ("3","Default heuristic/scripted models, no verified OpenAI run","CONFIRMED","src/config.py; src/llm.py; no live call made"),
      ("4","POSIX executor fails on Windows","CONFIRMED","baseline collection exit 4, ModuleNotFoundError: resource"),
      ("5","Noninteractive demo can auto-approve tier-1","CONFIRMED baseline; REMOVED","original src/main.py lambda default; new default leaves pending"),
      ("6","Unverified reviewer metadata/permissive resume","CONFIRMED baseline; FIXED in mock application scope","original hitl_gate accepts bool/default reviewer; strict service review now"),
      ("7","SQL tool lacks learner authorization","CONFIRMED baseline; FIXED at tool boundary","original run_readonly_sql accepts all SELECT; now disabled"),
      ("8","Learner-derived thread ID is not authentication","CONFIRMED baseline; FIXED in application scope","legacy thread_config disabled; sessions and opaque registry now"),
      ("9","Missing report/deck/video in baseline ZIP","CONFIRMED","original ZIP member manifest; report/deck now created; video still pending"),
      ("10","Saved textual demo is not a video","No baseline demo-text artifact independently found; no video found","Text and notebook outputs are not counted as a recording"),
      ("11","Latency claim lacks reproducible benchmark evidence","CONFIRMED baseline; NEW evidence added","old README claimed approx 1ms p95; old test warm only; raw cold/warm samples now"),
      ("12","80% waiting-time target","CONFIRMED by user working notes; original audio NOT VERIFIED","Original charter and new working notes; no achieved improvement claimed"),
    ]
    rubric=[
      {"criterion":"Functional completeness","maximum":35,"estimate":22,"risk":"Sandbox and genuine LLM behavior unverified; RAG cold misses"},
      {"criterion":"Quality and reproducibility","maximum":20,"estimate":15,"risk":"Offline evidence strong; production auth/persistence absent"},
      {"criterion":"Integration across both sprints","maximum":15,"estimate":9,"risk":"Real graph integration; grading/LLM path only partial"},
      {"criterion":"Technical report PDF","maximum":10,"estimate":9,"risk":"Report describes current limitations; evaluator judgement varies"},
      {"criterion":"Stakeholder presentation","maximum":10,"estimate":9,"risk":"10 slides delivered; original media unavailable"},
      {"criterion":"Recorded demonstration","maximum":10,"estimate":0,"risk":"Video missing"},
    ]
    result={"source_basis":"User working assignment/discovery/rubric transcriptions, not original media","functional":f,"acceptance":a,"deliverables":d,"source_and_discovery":s,"independent_findings":findings,
            "rubric":rubric,"estimated_score":sum(x["estimate"] for x in rubric),"estimate_range":[50,70],"pass_score":60,"verdict":"NOT READY"}
    (out/"requirements_matrix.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    lines=["# Requirement-by-requirement audit","","> Source basis: user-supplied working transcriptions. Original kickoff PPTX, discovery MP3 and assignment-page snapshot were unavailable. PASS means the stated offline/POC scope is demonstrated, not production readiness.","","Baseline execution: syntax exit 0; existing-environment pip check exit 0; pytest collection exit 4 due to Windows resource import. No original unsafe snippets were run.",""]
    for title,items in [("10 functional requirements",f),("5 acceptance criteria",a),("Deliverables",d),("Kickoff and discovery",s)]:
        lines += ["## "+title,"","| ID | Requirement | Baseline | Final | Code reference | Execution evidence and limitation |","|---|---|---|---|---|---|"]
        for x in items:
            lines.append("| "+" | ".join(str(v).replace("|","/").replace("\n"," ") for v in [x["id"],x["requirement"],x["baseline"],x["final"],x["code"],x["execution_evidence"]+". "+x["limits"]])+" |")
        lines.append("")
    lines += ["## Independent findings","","| # | Finding | Verification | Evidence |","|---|---|---|---|"]
    lines += ["| "+" | ".join(x)+" |" for x in findings]
    lines += ["","## Grading risk estimate","","This is a planning estimate, not an official grade or a predicted pass. The supplied category weights are used; partial-credit amounts are reviewer estimates with no official subcriteria. Estimated 64/100, plausible range 50-70. Passing score is 60. Critical safety/demonstration gaps override the numeric estimate: NOT READY.","","| Category | Maximum | Estimate | Risk |","|---|---:|---:|---|"]
    lines += [f"| {x['criterion']} | {x['maximum']} | {x['estimate']} | {x['risk']} |" for x in rubric]
    (out/"requirements_matrix.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"requirements":len(f)+len(a)+len(d)+len(s),"functional":len(f),"acceptance":len(a),"estimate":result["estimated_score"],"verdict":result["verdict"]}))
if __name__=="__main__":main()
