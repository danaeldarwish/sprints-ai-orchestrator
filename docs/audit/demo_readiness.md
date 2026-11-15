# Demonstration and submission preparation - NOT READY

## A. Changes made

Added an explicit application startup gate and CLI readiness command. It prepares actual Chroma before exposing the learner service; no LangGraph architecture rebuild or sandbox changes. Prepared gpt-6-luna parameters, shared24-attempt and estimated-cost admission, current operator project/quota/pricing preflight and future response/usage/exit-code capture. Refreshed the16-page technical report and10-slide editable presentation/PDF as separate current files. All original successful evidence, old report/deck and finalZIP remain preserved.

The preserved complete suite has157passed,0failed,0skipped, including14sandbox categories plus2real-container regressions. Scoped startup/model tests:70passed,0failed,0skipped; actual process exit0. No full security rerun, Docker rebuild or dependency installation. Commands, logs and JUnit are in evidence/demonstration_20261115. Earlier failed attempts remain available.

## B. Readiness and latency

The serving CLI returns READY only after a real vector collection query and graph construction succeed. Startup failure returns UNAVAILABLE with no learner service and exit2. The trusted warm=False option is only a fixture/benchmark bypass and must not be used in a serving host. Fresh startup completed in3042.505ms (one observation, not a benchmark).

[Operational1000ms contract](../rag_readiness.md): retrieval after successful mandatory preparation, measured from retrieve entry to source-bearing result. It excludes process imports, startup preparation, LLM output and human wait. That interpretation requires assessor agreement and does not change the original general criterion. Cold acceptance remains PARTIAL. Preserved p95 values: unprepared1591.568ms(n20); prepared-first13.129ms(n20); warm16.128ms(n200). Startup preparation p95=1913.966ms. All outliers and raw distributions remain in evidence/followup_20261115/rag_latency.json; no cold-query speedup is claimed.

## C-D. OpenAI preflight and future command

**NOT EXECUTED: zero OpenAI requests and no credentials accessed.** Official documentation lists gpt-6-luna and supports Chat Completions function calls with reasoning_effort=none. Old gpt-4o-mini-2024-07-18 shutdown:14January2027. Project model access, authorization and quota are **PENDING**; public docs do not prove these facts.

The [complete plan](../live_verification_plan.md) fixes24total completion attempts including parser repairs/failures, conservative12000input admission,500output,20s timeout,0SDK retries and two total parser attempts. Input uses max(local tokens,UTF-8 bytes)+1024. Standard global price input$0.10/M,cache writes$0.125/M,output$0.50/M. Conservative estimated reservation$0.00175/attempt,$0.042maximum under$0.05ceiling. Stop before dispatch on cost/request exhaustion; stop subsequent attempts on any provider error, missing/invalid usage or over-envelope usage. Any partial/unexecuted case remains partial. Dedicated SPRINTS_VERIFICATION_API_KEY only, after separate approval and current preflight; no ambient key/dotenv reuse. No model fallback.

~~~powershell
# NOT EXECUTED. Only after separate explicit approval, current project preflight,
# dedicated credential provisioning, exact model/authorization and image setup:
.\.venv-audit\Scripts\python.exe scripts/verify_openai.py --execute --approval-id APPROVAL_REFERENCE --preflight-file .build/private/openai_preflight.json --output evidence/live_NEW_TIMESTAMP
~~~

Complete environment setup, cleanup and evidence instructions are in the linked plan. The prepared harness will capture worker stdout/stderr, live_results.json and process_exit.json; no result or exit code is invented before that run.

## E. Genuine demonstration preparation

[Exact preparation commands,4:30sequence and capture checklist](../demo_recording_script.md). In a real terminal, after setting offline/hash mode, separate demo data/index paths and the verified image:

~~~powershell
.\.venv-audit\Scripts\python.exe -m src.main build-db
.\.venv-audit\Scripts\python.exe -m src.main ingest
.\.venv-audit\Scripts\python.exe -m src.main readiness
.\.venv-audit\Scripts\python.exe -m src.main sandbox-status
.\.venv-audit\Scripts\python.exe -m src.main demo --verbose
.\.venv-audit\Scripts\python.exe -m src.main review-demo
# Human explicitly enters APPROVE and rationale.
.\.venv-audit\Scripts\python.exe -m src.main review-demo
# Human explicitly enters REJECT and rationale for a fresh proposal.
~~~

Show cited Q&A, actual Docker grading/structured feedback, deterministic optimizer/judge, actual SQLite progress/EGP/preference rows, grounded employer matching and withheld Fawry pending review. Default demo never approves. Real terminal input is mandatory for review; automated mock-reviewer test transitions do not count as a human recording. The preserved executed notebook shows actual container grading and labeled grader fault injection. VIDEO STATUS=PENDING; no video or duration claim is fabricated. Actual footage must be180-300seconds, played and checked for readable output, then hashed. No publication authorized.

## F-G. Deliverables

| Deliverable | Current status |
|---|---|
| Source and existing/new tests, dependency lock, pinned image recipe | Present locally; no Git metadata or shareable source URL |
| Executed notebook | notebooks/evaluator_optimizer_verified.ipynb;4executed code cells,0errors; unchanged |
| Original CSV / documented SQLite |25learners;16synthetic openings; original bytes unchanged |
| Updated technical report | [16-page PDF](../../submission/technical_report_current.pdf) |
| Updated stakeholder deck | [10-slide PPTX](../../submission/stakeholder_presentation_current.pptx) / [10-page PDF](../../submission/stakeholder_presentation_current.pdf) |
| Genuine video or recording link | Missing/PENDING |
| Shareable repository/workspace URL | Missing; no publishing or push authorized |
| Existing final ZIP | Preserved older snapshot, not current source-complete; intentionally not overwritten |

[Current requirements matrix](requirements_matrix_demo.md). Security limits remain: shared kernel/daemon trust, same-interpreter grading integrity after policy escape, mock identity and process-local ownership/review/audit/checkpoints. No production deployment, durable identity/store, broad load validation or current employer feeds. Curriculum/openings are synthetic. Original kickoff PPTX/MP3 and assignment-page fidelity remain unverified. The80%waiting-time reduction is a target with0business observations.

## H. Verdict

**NOT READY for final submission.** Local startup, safe demo instructions and refreshed report/deck are prepared. Remaining gates: separately authorized genuine LLM evaluation; genuine3-5minute recording; shareable source link; assessor agreement or resolution of cold retrieval; and a new verified final package after those gates. No official numerical grade is assigned. Missing recording risks all10video rubric points. No paid API call, credential reuse, publishing, GitHub push or final submission occurred.
