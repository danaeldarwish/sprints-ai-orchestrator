# Current requirements matrix

Based on user working notes; original media remain unavailable. Preserved earlier matrices are unchanged.

## functional

| ID | Requirement | Status | Scope |
|---|---|---|---|
| F1 | 500-token Chroma ingestion, 50-token overlap | PASS | Actual Chroma, exact cl100k_base; embeddings are deterministic hashing. |
| F2 | Pydantic score, feedback_points, pass_status | PASS | Real container-backed Pydantic feedback in the executed notebook; live model grading pending. |
| F3 | SQL learner progress, EGP target, employers | PASS | Actual SQLite rows; partner openings synthetic. |
| F4 | Secure isolated Python execution | PASS | Actual Linux controls/kernel evidence; see original 14 plus two new real tests. Shared-kernel and same-interpreter verdict-integrity risks remain. |
| F5 | Unified TypedDict StateGraph, Advisor/Assessor routing | PASS | Real LangGraph execution with offline reasoning. |
| F6 | MemorySaver and learner checkpoint isolation | PASS | Mock authenticated application context only; process-local persistence. |
| F7 | Agentic RAG critique, reformulation and retry | PARTIAL | Real retrieval and bounded reflection/reformulation; critique remains heuristic until approved live inference. |
| F8 | Assessor evaluator-optimizer with LLM-as-Judge | PARTIAL | New actual-container notebook executed; optimizer grader fault injection labeled. Genuine LLM judge pending. |
| F9 | Tier-1 LangGraph interrupt and explicit authorized review | PASS | Pending/approved/rejected transitions use mock reviewer sessions. Production identity and a real human recording remain unverified. |
| F10 | HumanMessage, AIMessage, ToolMessage and trace logs | PASS | Metadata-only trace excludes records and tokens. |

## acceptance

| ID | Requirement | Status | Scope |
|---|---|---|---|
| A1 | Use LangGraph orchestration | PASS |  |
| A2 | Detailed Sprints-specific docstrings | PASS | Editorial review, not a claim that a style tool proved documentation quality. |
| A3 | Chroma retrieval below 1000 ms | PARTIAL | PARTIAL: unprepared cold misses retained. Operational prepared-query interpretation and startup READY/UNAVAILABLE gate documented in docs/rag_readiness.md; assessor agreement pending. |
| A4 | SQL/Python failures return structured Unable to verify | PASS |  |
| A5 | At most three optimizer refinements | PASS | Three refinements/four drafts maximum; actual execution and labeled grader fault injection tested separately. |

## deliverables

| ID | Requirement | Status | Scope |
|---|---|---|---|
| D1 | Reproducible GitHub-ready repository | PARTIAL | Local source/lock/image recipe exists; no Git metadata or shareable repository/workspace URL. |
| D2 | Complete technical report PDF | PASS | Updated16-page technical report; actual security evidence and current model preflight disclosed. |
| D3 | 8-10 slide presentation in PPTX and PDF | PASS | Updated10editable slides and faithful rendered PDF; original deck preserved. |
| D4 | Genuine 3-5 minute recorded demo | FAIL | VIDEO STATUS=PENDING. No genuine 180–300 s recording/link; planned 4:30 script is not a video. |
| D5 | Executed assessor evaluation notebook | PASS | Original notebook retained; new actual-container notebook executed with no errors. |
| D6 | Final package and audit manifest | PARTIAL | Existing final ZIP preserved unchanged. It excludes follow-up changes; not a current submission. |
| D7 | Supplied learner data and documented SQLite | PASS | 25 learner records unchanged; 16 synthetic openings. No 500-record expansion. |
| D8 | Shareable repository or workspace URL | PENDING | No publication authorized; no URL invented. |

## source and discovery

| ID | Requirement | Status | Scope |
|---|---|---|---|
| K1 | Original kickoff PPTX content cross-check | NOT VERIFIED | Working notes cannot prove full deck fidelity. |
| K2 | Kickoff mentions 500 learners | NOT VERIFIED | 500 remains an attributed independent finding, not independently verified media content. |
| K3 | Original discovery MP3 and full transcript cross-check | NOT VERIFIED | Original MP3 and verbatim full transcript unavailable. |
| S1 | 80% waiting-time reduction target, honest measurement | PASS | Target captured; achieved reduction NOT VERIFIED. |
| S2 | Mandatory typed state and per-learner checkpoints | PASS |  |
| S3 | Secure grading required by discovery | PASS | Actual scoped Linux tests/probes; static/mocked cases are separate evidence. |
| S4 | Prevent invented qualifications and wrong matches | PASS | Deterministic row-derived POC policy; real partner-policy validity unverified. |
| S5 | Live Q&A, isolated grading and DB matching demo | PARTIAL | Local graph/tools evaluated; paid inference, genuine recording and publication remain pending. |

