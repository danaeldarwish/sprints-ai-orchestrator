"""Create the technical report from measured evidence; no generated results."""
from pathlib import Path
import json,xml.etree.ElementTree as ET
from html import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,KeepTogether
from reportlab.graphics.shapes import Drawing,Rect,String,Line,Polygon
ROOT=Path(__file__).resolve().parents[1]
NAVY=colors.HexColor("#13263D");TEAL=colors.HexColor("#087E8B");MUTED=colors.HexColor("#526477")
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name="BodyAudit",fontName="Helvetica",fontSize=10.4,leading=15,spaceAfter=10,textColor=NAVY))
styles.add(ParagraphStyle(name="SmallAudit",fontName="Helvetica",fontSize=8.6,leading=12,spaceAfter=7,textColor=MUTED))
styles.add(ParagraphStyle(name="TitleAudit",fontName="Helvetica-Bold",fontSize=31,leading=36,spaceAfter=20,textColor=NAVY))
styles.add(ParagraphStyle(name="HeadingAudit",fontName="Helvetica-Bold",fontSize=22,leading=27,spaceAfter=17,textColor=NAVY))
styles.add(ParagraphStyle(name="SubAudit",fontName="Helvetica-Bold",fontSize=12,leading=16,spaceAfter=8,textColor=TEAL))
styles.add(ParagraphStyle(name="HeaderAudit",parent=styles["SmallAudit"],fontName="Helvetica-Bold",textColor=colors.white))
def p(text,small=False):return Paragraph(text,styles["SmallAudit" if small else "BodyAudit"])
def table(rows,widths=None):
    data=[[Paragraph(escape(str(cell)),styles["HeaderAudit"] if i==0 else styles["SmallAudit"]) for cell in row] for i,row in enumerate(rows)]
    t=Table(data,colWidths=widths,repeatRows=1,hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),colors.white),
                          ("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),9),
                          ("RIGHTPADDING",(0,0),(-1,-1),9),("TOPPADDING",(0,0),(-1,-1),8),
                          ("BOTTOMPADDING",(0,0),(-1,-1),7),("LINEBELOW",(0,0),(-1,0),1,TEAL),
                          ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#F0F4F7"),colors.white])]))
    return t
def architecture():
    d=Drawing(480,320)
    nodes={"User":(130,265,220,40,"Mock-authenticated learner"),
           "App":(130,200,220,40,"Application boundary + owned thread"),
           "Graph":(130,135,220,40,"LangGraph typed state / MemorySaver"),
           "Adv":(0,65,210,40,"Advisor: Chroma + scoped SQLite"),
           "Ass":(270,65,210,40,"Assessor: container-only execution"),
           "Review":(0,0,210,40,"Tier-1 interrupt / scoped review"),
           "Grade":(270,0,210,40,"Structured grade / bounded judge")}
    for key,(x,y,w,h,label) in nodes.items():
        d.add(Rect(x,y,w,h,fillColor=colors.HexColor("#EDF5F6"),strokeColor=TEAL,strokeWidth=1))
        d.add(String(x+w/2,y+h/2-3,label,textAnchor="middle",fontName="Helvetica",fontSize=9,fillColor=NAVY))
    for a,b in [("User","App"),("App","Graph"),("Graph","Adv"),("Graph","Ass"),("Adv","Review"),("Ass","Grade")]:
        ax,ay,aw,ah,_=nodes[a];bx,by,bw,bh,_=nodes[b]
        x1=ax+aw/2;y1=ay;x2=bx+bw/2;y2=by+bh
        d.add(Line(x1,y1,x2,y2,strokeColor=MUTED,strokeWidth=1))
        d.add(Polygon([x2,y2,x2-3,y2+6,x2+3,y2+6],fillColor=MUTED,strokeColor=MUTED))
    return d
def main():
    audit=json.loads((ROOT/"docs/audit/requirements_matrix_followup.json").read_text())
    bench=json.loads((ROOT/"evidence/followup_20261115/rag_latency.json").read_text())
    suite=ET.parse(ROOT/"evidence/followup_20261115/verified_pid/full_tests.xml").getroot().find("testsuite")
    tests=int(suite.attrib["tests"]);skipped=int(suite.attrib["skipped"]);failures=int(suite.attrib["failures"])+int(suite.attrib["errors"]);passed=tests-skipped-failures
    output=ROOT/"submission"/"technical_report_current.pdf"
    story=[]
    def page(title,*items):
        if story:story.append(PageBreak())
        story.append(Paragraph(title,styles["HeadingAudit"]))
        for item in items:
            story.append(p(item) if isinstance(item,str) else item)
            if isinstance(item,(Drawing,Table)):story.append(Spacer(1,12))
    story += [Spacer(1,70),Paragraph("Sprints Multi-Agent AI<br/>Career &amp; Assessment<br/>Orchestrator",styles["TitleAudit"]),
              p("Technical audit and remediation report<br/>15 November 2026 - updated demonstration preparation",True),Spacer(1,26),
              Paragraph("Submission verdict: NOT READY",styles["HeadingAudit"]),
              p("The existing solution now has an authenticated mock application boundary, scoped SQL tools, one-time authorized review and a container-only execution path. Offline evidence is reproducible. Actual Docker grading is verified in the preserved local evidence. Live model judgement remains unverified; the recorded demonstration is pending."),
              table([["Verified offline","Still open"],[f"{passed} tests passed; {skipped} skipped in preserved full suite","Cold retrieval criterion and production security limitations"],["Actual LangGraph, ChromaDB, SQLite and MemorySaver","Paid OpenAI inference, requiring explicit authorization"],["Report, stakeholder deck and executed notebook","Genuine 3-5 minute demonstration video"]],[240,240]),
              Spacer(1,18),p("No new numerical grade is assigned. The earlier 64/100 estimate is historical and must not be used as a predicted pass. The supplied project pass score is 60.",True)]
    page("1. Business problem and charter",
         "The Sprints workflow combines curriculum support, Python assessment and placement advice. The working discovery notes identify secure code grading, correct learner/employer matching and a unified per-learner graph as mandatory. The stakeholder target is an 80% reduction in student waiting time; this audit has no measured queue baseline or pilot outcomes.",
         table([["Stakeholder","Need and control"],["Learner","Relevant curriculum answer, specific assessment feedback and private records"],["Student Success / career reviewer","Grounded recommendations and explicit authority over tier-1 releases"],["Engineering / security","Reproducibility, bounded execution, ownership checks and honest failure handling"],["Graduation reviewer","Traceable requirement evidence, report, slides, notebook and real recording"]],[160,320]),
         "Scope: audit and correct the existing implementation without replacing its LangGraph design. Out of scope: production hosting, real partner feeds, durable identity/checkpoint infrastructure and unauthorized paid calls.",
         p("Sources: _client_sources/assignment_requirements.md; client_discovery_call_transcript.md; grading_rubric.md. These are user-supplied working transcriptions. Original PPTX, MP3 and assignment-page snapshot are unavailable. No names or requirements absent from these notes are represented as independently verified.",True))
    page("2. System architecture",architecture(),
         "The trusted application resolves mock sessions, allocates an opaque checkpoint thread and accepts a strict text request. The graph routes to curriculum retrieval, scoped database matching or assessment. A tier-1 draft pauses before the public response releases it.",
         "Real offline components: LangGraph execution and interrupt checkpoints, ChromaDB persistence/query, SQLite queries and Pydantic parsing. Simulated components: language decisions use HeuristicReasoner and ScriptedChatModel; the new executed notebook uses actual containers and explicitly labeled grader fault injection. The judge remains deterministic, not an LLM.",
         p("Code: src/service.py; src/agents/orchestrator.py; src/state.py; docs/architecture.mmd. The diagram describes the implementation, not a deployed system.",True))
    page("3. LangGraph state and routing",
         table([["State area","Fields and behavior"],["Message protocol","messages uses add_messages and retains HumanMessage, AIMessage and ToolMessage"],["Persistent learner context","learner_id from trusted application, turn_count and last_topic persist per owned thread"],["Routing and retrieval","intent, route, search_query, tried_queries, attempts, retrieved context and sufficiency"],["Career review","profile, openings, recommendation, requires_approval, pending_id and approval"],["Assessment","assignment, code, evidence, assessment, judge, issues, refinements and grader_calls"],["Output and failure","status, final_answer and structured fallback"]],[155,325]),
         "The orchestrator resets per-turn scratch data while preserving conversation context. Code submissions route to the Assessor; career intent routes to scoped SQL; other course questions route to the Advisor. Unknown or incomplete inputs receive clarification.",
         "Provider exceptions in routing/reflection/answering degrade to structured Unable to verify. A failing grader does the same; an unavailable judge exhausts the bounded review loop and leaves a provisional grade.",
         p("Evidence: tests/test_graph.py; tests/test_security_regressions.py; evidence/followup_20261115/verified_pid/full_tests.xml. These execute the real graph with offline reasoning.",True))
    page("4. Curriculum ingestion and agentic RAG",
         f"Six synthetic curriculum files produce {bench['proof']['ingest']['chunks']} chunks in the measured corpus. The maximum actual chunk size is {bench['proof']['ingest']['max_chunk_tokens']} cl100k_base tokens. Adjacent windows overlap by exactly 50 token positions; final windows may be shorter than 500. Unicode boundary checks prevent broken UTF-8. Missing exact tokenization raises an explicit error instead of silently estimating.",
         "The hash embedder normalizes deterministic term and bigram features. ChromaDB stores vectors, text and source metadata. It is actual vector retrieval, but it is not a verified hosted embedding model. Metadata records token_start, token_end, chunk index, token count and overlap.",
         "Advisor flow: retrieve, critique sufficiency, reformulate if insufficient, retrieve again, then answer or abstain. The graph permits at most three searches, including the initial search. Offline sufficiency uses term coverage; live LLM reflection remains unverified.",
         "Answers attribute source files. This audit corrected synthetic material that previously implied thread IDs alone guaranteed privacy or that a host subprocess was an adequate sandbox. Source hashes accompany the final benchmark.",
         p("Code: src/tokens.py; src/tools/rag_retriever.py; src/agents/advisor_agent.py. Evidence: tests/test_rag.py; exact-overlap regression; evidence/followup_20261115/rag_latency.json.",True))
    page("5. SQLite records and career matching",
         "The supplied CSV contains 25 learner records and remains byte-for-byte unchanged. The original SQLite file also remains unchanged. The database builder materializes those learners and 16 synthetic openings. No rows were duplicated to pretend that 500 client learners were supplied.",
         table([["Table / operation","Stored evidence"],["learners","Track, completed modules, stored Python score, EGP target, preferred employers and readiness"],["partner_openings","Role, track, minimum modules/score, EGP salary band, tier and is_synthetic=1"],["get_learner_profile","Parameterized exact learner lookup, independently checked against trusted context"],["list_matching_openings","Scoped profile plus row-derived eligibility; unrestricted SELECT tool disabled"]],[155,325]),
         "Matching checks readiness, track, employer preferences, module completion, stored score and target salary against each opening band. Learner-facing text comes from the retrieved rows. Grounding regressions reject invented employer, salary and opening facts.",
         "New assessment results do not automatically overwrite the client grade record. The learner pass mark 70 and 70/15/15 grading rubric are POC choices, distinct from the project pass score 60. Salary bands and vacancies are synthetic, not current employer commitments.",
         p("Code: src/tools/db_queries.py; src/agents/advisor_agent.py. Evidence: tests/test_sql_tool.py; evidence/followup_20261115/evaluation/scenarios.json; docs/data_provenance.md.",True))
    page("6. Container-only code execution",
         "No submitted Python executes on the Windows host. The old POSIX resource/preexec_fn path has been removed. The replacement requires an approved immutable local Linux image and a capable local Docker daemon. Missing or unsupported isolation returns Unable to verify and no grade.",
         table([["Verified local control","Implementation"],["Network / identity","network none; UID/GID 65534; capabilities dropped; no-new-privileges; default seccomp"],["Filesystem / credentials","Read-only root; no host mounts; bounded noexec/nosuid/nodev temporary filesystem; clean environment/config"],["Resources","512 MiB memory and equal swap ceiling, half CPU, 32 processes, CPU/file/core/descriptor limits"],["Capture / lifetime","Per-submission container; capped stdout and stderr; 5 s execution deadline; authoritative exit/OOM capture; mandatory force removal"]],[150,330]),
         "Observed result: Docker Desktop 4.97.0 / Linux Engine 29.9.2 on WSL2 is available. All 14 sandbox categories and two extra real-container regressions passed. The corrected PID probe attempts forks against the unchanged 32-task cap and requires the cgroup limit-hit counter to increase. Earlier failing runs remain preserved. Static/mocked checks are separate evidence.",
         "AST screening and restricted builtins add defense in depth. The current harness shares an interpreter with submitted code, leaving verdict integrity after a language-policy escape as a separate limitation. A stronger production sandbox and separate trusted test orchestration are recommended.",
         p("Evidence: tests/test_sandbox.py; evidence/followup_20261115/verified_pid/full_tests.xml; evidence/followup_20261115/evaluation/scenarios.json. Intended Docker policy follows official running-container and resource-control documentation linked in docs/security_model.md.",True))
    page("7. Structured grading and bounded optimization",
         "AssessmentResult defines score (0-100), feedback_points and pass_status. The local rubric allocates 70 correctness points, 15 execution-hygiene points and 15 readability points. These are transparent POC assumptions, not the graduation scoring rubric.",
         "Flow: isolated execution, structured draft, judge review, then finalize or refine feedback using judge issues. A maximum of three refinements means one initial grade plus up to three additional grader calls. An unapproved result remains provisional and requires human review.",
         table([["Test case","Observed result and evidence kind"],["Honest grade","Accepted on initial pass with offline deterministic grading; real-container notebook separately retained"],["Inflated first grade","Judge detects inconsistency; optimizer corrects after one refinement"],["Repeated inflated grade","Stops at three refinements / four grader and judge calls; provisional"],["Judge or grader unavailable","Provisional result or structured fallback; no fabricated final grade"],["Actual buggy / corrected submissions","Both graded using actual isolated execution; structured scores and feedback retained"]],[160,320]),
         "The new evaluator_optimizer_verified.ipynb contains four executed code cells and zero errors. Real containers grade buggy/corrected submissions. Injected grader faults exercise one refinement and the three-refinement cap. The deterministic judge and injected grader remain explicitly labeled.",
         p("Code: src/agents/assessor_agent.py; src/rubric.py; src/llm.py. Evidence: tests/test_evaluator_optimizer.py; notebooks/evaluator_optimizer_verified.ipynb; evidence/followup_20261115/notebook_execution.json.",True))
    page("8. Identity, memory and learner isolation",
         "MockIdentityProvider issues random sessions during trusted local application startup. Learner requests cannot select identity or role. This simulates an identity provider for the POC; it does not authenticate real people and must not be exposed as a username-only public login endpoint.",
         "OrchestratorService owns opaque thread allocation and the private MemorySaver graph. Strict request validation rejects learner_id, thread_id, raw messages, approval, profile and code-state injection. Snapshot access resolves the requesting session and returns an explicit public field allowlist.",
         "Database tools independently enforce the bound learner context, even if a prompt supplies a different ID. Parameterized operations prevent SQL injection; ad-hoc SQL remains disabled. Real tool execution tests demonstrate ContextVar propagation and cleanup.",
         table([["Boundary tested","Result"],["Another learner profile or salary query","Structured denial at the database tool"],["Thread / checkpoint selection in request","Strict validation failure"],["Learner or unassigned reviewer approval","Authorization denial"],["Concurrent learner contexts","Own records remain separate"],["Cross-thread memory and follow-up","Own context persists; other learner count starts at one"]],[240,240]),
         "The graph and private Python attributes are trusted application internals, not a security boundary against someone controlling the host interpreter. Sessions, locks and MemorySaver are process-local. Production needs durable transactional ownership, trusted identity and transport security.",
         p("Evidence: tests/test_graph.py; tests/test_security_regressions.py; evidence/followup_20261115/evaluation/scenarios.json.",True))
    page("9. Human-in-the-loop authorization",
         "A tier-1 placement pauses using LangGraph interrupt. The learner sees only a pending message; raw draft, profile and tool responses stay internal. The default demo never resumes an approval automatically.",
         "The reviewer session must have learner scope. Strict Pydantic review requires a pending ID, boolean approval and rationale. The service compares the current pending checkpoint and complete structured-recommendation hash, binds trusted review context, atomically consumes the pending action and resumes under a lock.",
         table([["Transition / attack","Observed behavior"],["New tier-1 draft","Pending; no Fawry draft released to learner"],["Explicit scoped reviewer approval fixture","Recommendation released through the real resumed graph"],["Explicit scoped rejection fixture","Recommendation withheld"],["Forged reviewer metadata or malformed boolean","Rejected before resume"],["Replayed / racing decisions","At most one decision accepted"],["New learner request during pending review","Denied; pending state cannot be overwritten"]],[230,250]),
         "Approval and rejection evidence uses automated API tests with application-issued mock reviewer sessions. It proves application transitions, not that a real human performed a recorded review. The interactive review command requires actual terminal input. Audit events record timestamp, pending ID, action and role without bearer tokens, notes or learner records.",
         p("Code: src/service.py:ReviewDecision and review; src/auth.py:require_review; src/agents/advisor_agent.py:hitl_gate. Evidence: named security tests and scenarios JSON.",True))
    rows=[["Measurement","n","p50 ms","p95 ms","p99 ms","Max ms","<1000 ms"]]
    for label,key in [("Process cold","cold_process"),("Cold first retrieval","cold_first_retrieve"),("Startup preparation","startup_readiness"),("Prepared first query","first_after_readiness"),("Warm retrieval","warm")]:
        x=bench[key];rows.append([label,x["n"],x["p50_ms"],x["p95_ms"],x["p99_ms"],x["max_ms"],str(x["below_1000ms_pct"])+"%"])
    page("10. Reproducible retrieval benchmarks",
         table(rows,[107,42,64,64,64,70,69]),
         "All measurements use real local ChromaDB with deterministic hashing embeddings. Percentiles use nearest rank. Twenty alternating fresh-process pairs measure unprepared retrieval versus explicit readiness. Two hundred warm queries rotate five fixed queries. Raw samples, corpus hashes and token-window metadata are retained.",
         "Process-cold time includes interpreter startup, imports, index initialization and retrieval. Cold-first-retrieval time excludes imports but includes lazy client/collection startup. The OS file cache was not flushed; these are process-cold measurements, not disk-cold benchmarks. Warm retrieval includes query embedding and executor dispatch.",
         "The warm sample meets the 1000 ms criterion. Cold first queries can exceed it, so the general acceptance criterion remains partial. Startup preparation moves initialization ahead of request admission; no improvement in unprepared retrieval is claimed. src/startup.py returns READY only after a real collection query and graph initialization succeed. Failure returns UNAVAILABLE, exposes no service and exits the CLI with code 2. The prepared-query interpretation requires assessor agreement and is not an unconditional guarantee. This is a small synthetic corpus and a single Windows host; it does not establish throughput or 500-learner scale.",
         "An earlier run measured valid samples but exited with a Windows Chroma-file cleanup error. Its logs remain preserved. The corrected benchmark runs Chroma workers in child processes so handles close before the parent removes its temporary index.",
         p("Preserved benchmark: scripts/benchmark_readiness.py. Runtime gate: python -m src.main readiness. Evidence: evidence/followup_20261115/rag_latency.json; evidence/commands/rag_benchmark.json and preserved earlier attempts.",True))
    page("11. End-to-end evaluation and evidence",
         table([["Scenario","Observed result","Evidence category"],["Curriculum Q&A","Sources and bounded reformulation","Real graph + Chroma; heuristic reflection"],["Buggy Python","Structured grade","Actual Linux container; deterministic reasoner"],["Corrected Python","100/100 in preserved run","Actual Linux container; deterministic judge"],["Career matching","Row-derived EGP matching","Actual scoped SQLite; synthetic openings"],["Tier-1 placement","Pending, approve/reject, replay denied","Real interrupt/resume; mock reviewer fixtures"],["Different learner","Profile/checkpoint/approval denied","Actual application and tool boundary"]],[125,150,205]),
         f"Expanded offline suite: {passed} passed, {skipped} skipped, {failures} failures/errors; process exit 0. No sandbox cases were skipped in this preserved full run. After the scoped startup/model changes, 70 focused offline tests passed; the expensive full sandbox suite was not repeated. The original suite could not collect on Windows (exit 4). Original source and tests remain in the baseline snapshot.",
         "The standard demo prints metadata-only Human/AI/Tool traces. Evaluation JSON and command logs retain real output, process exit codes and timestamps. No provider key, bearer session or full environment dump is recorded. Existing notebook output was preserved before re-execution.",
         p("Evidence locations: evidence/followup_20261115/verified_pid/full_tests.xml; evidence/commands; evidence/followup_20261115/evaluation/scenarios.json; evidence/baseline/original_source.zip. The existing ZIP is an unchanged older snapshot. It does not contain these changes and has not been resubmitted.",True))
    page("12. Business success measurement",
         "The 80% reduction is a stakeholder target, not an achieved result. Business waiting-time sample size in this audit is zero. No baseline queue timestamps, staff availability or post-deployment outcome observations were provided.",
         "Record case ID, activity, queue entry, service start, completion and outcome. Queue wait is service start minus queue entry. Learner end-to-end lead time is final completion minus initial submission and must be reported separately.",
         "Compare matched baseline and automation cohorts with the same activity mix, arrival profile, operating hours and staffing assumptions. Include human approval wait, rejected cases, errors and unresolved cases. Report n, completion rate, mean, median and p90 waits and lead times.",
         table([["Metric","Current status"],["Baseline mean wait","Unavailable"],["Pilot mean wait","Unavailable"],["Business evaluation sample","0 measured cases"],["Observed software latency","Separate Chroma/query and process timings"],["80% target test","Pilot mean wait <= 0.20 x measured baseline mean wait"]],[230,250]),
         "Reduction = 100 x (baseline mean wait - pilot mean wait) / baseline mean wait. A zero baseline makes the percentage undefined. A proposed pilot begins with at least 30 cases per activity per cohort and then reassesses uncertainty; this is not a sample-size guarantee.",
         p("Methodology: docs/business_metrics.md. Software retrieval speed cannot be substituted for business queue-time reduction.",True))
    reqrows=[["ID","Functional requirement","Final status"]]+[[x["id"],x["requirement"],x["final"]] for x in audit["functional"]]
    page("13. Requirement coverage",
         table(reqrows,[35,350,95]),
         "All five acceptance criteria are individually tracked in the full audit. LangGraph, documentation, structured failures and the three-refinement cap have offline evidence. The latency criterion remains partial because cold queries may miss 1000 ms.",
         "Kickoff and discovery requirements are based on user-supplied working notes. Original attached media are absent. The 500-learner kickoff claim and full fidelity to the original media cannot be independently verified.",
         p("Complete baseline/final matrices and code-line references: docs/audit/requirements_matrix_demo.md and .json. PASS is limited to the evidence scope in each row.",True))
    page("14. OpenAI verification preflight",
         "STATUS: NOT EXECUTED. Public official documentation recommends gpt-6-luna as the replacement for gpt-4o-mini-2024-07-18, which has a published shutdown date of 14 January 2027. Project entitlement, authorization and billing/quota have not been checked; no OpenAI request or credential access occurred.",
         table([["Control","Prepared envelope"],["Endpoint / model","Chat Completions; exact gpt-6-luna; reasoning_effort=none; Standard processing"],["Attempts and tokens","24 shared total attempts including failures/repairs; conservative input admission 12000; output 500; n=1"],["Timeout / retry","20 s per attempt; zero SDK retries; at most two total parser attempts"],["Estimated cost","Ordinary uncached envelope $0.0348; conservative cache-write envelope $0.042; estimated-cost ceiling $0.05"],["Stop policy","Any provider error, exhausted request/cost reservation, missing usage or token overrun stops later dispatch"]],[150,330]),
         "The adapter uses the same LangChain chat and scoped SQLite tool architecture. Request-shape and cost-stop tests use httpx.MockTransport only. Input admission takes the larger of local token count and serialized UTF-8 bytes, plus 1024 tokens; strict admission can leave cases unexecuted. The estimate is not an exact billing guarantee.",
         "The operator must copy docs/openai_preflight.template.json to a private local file and verify intended-project model access, authorization, quota and Standard global pricing within 24 hours. The CLI rejects incomplete, stale or changed-price attestations before reading SPRINTS_VERIFICATION_API_KEY. No ambient key or dotenv is used.",
         p("NOT EXECUTED: python scripts/verify_openai.py --execute --approval-id APPROVAL_REFERENCE --preflight-file .build/private/openai_preflight.json --output evidence/live_NEW_TIMESTAMP. First set the exact model, explicit authorization and verified image in the approved process. See docs/live_verification_plan.md for complete safe setup.",True),
         p("Official sources checked 15 November 2026: developers.openai.com/api/docs/models/gpt-6-luna; /api/docs/pricing; /api/docs/deprecations. Input $0.10/M, cache writes $0.125/M, output $0.50/M. These public facts do not establish this project's account access or actual model behavior.",True))
    page("15. Rubric risk and release gates",
         table([["Category","Maximum","Current numerical grade"]]+[[x["criterion"],x["maximum"],(x["estimate"] if x["estimate"] is not None else "Not assigned")] for x in audit["rubric"]]+[["Total",100,"Not assigned"]],[300,90,90]),
         "The user-supplied weights remain 35/20/15/10/10/10, with pass threshold 60. No updated score is invented. Missing video risks the entire 10-point recording category; live LLM behavior and cold retrieval remain partial. Original media fidelity is unverified.",
         "Remaining gates: separately authorize and execute the controlled OpenAI verification; record and inspect a genuine 3-5 minute walkthrough; supply a shareable source URL; agree or resolve the cold-retrieval limitation; refresh the final package only after those gates. Original kickoff PPTX/MP3 remain absent.",
         "The report, 10-slide PPTX/PDF and executed notebook are local artifacts. The video remains PENDING with an exact recording script and checklist. Current artifact hashes and the preserved ZIP hash are recorded in evidence/demonstration_20261115. The existing submission manifest describes its earlier ZIP snapshot.",
         p("Primary references: user working notes in _client_sources; official OpenAI model/pricing/deprecation pages linked in docs/live_verification_plan.md; official Docker run/resource pages linked in docs/security_model.md. Final verdict: NOT READY.",True))
    def chrome(canvas,doc):
        canvas.saveState()
        canvas.setFillColor(MUTED);canvas.setFont("Helvetica",8)
        canvas.drawString(52,27,"Sprints graduation audit - 15 November 2026 - offline evidence")
        canvas.drawRightString(A4[0]-52,27,str(doc.page))
        if doc.page>1:
            canvas.setStrokeColor(TEAL);canvas.line(52,A4[1]-37,A4[0]-52,A4[1]-37)
        canvas.restoreState()
    doc=SimpleDocTemplate(str(output),pagesize=A4,rightMargin=52,leftMargin=52,topMargin=55,bottomMargin=48,title="Sprints Orchestrator Technical Audit",author="Sprints Project Review",allowSplitting=1)
    doc.build(story,onFirstPage=chrome,onLaterPages=chrome)
    print(output)
if __name__=="__main__":main()
