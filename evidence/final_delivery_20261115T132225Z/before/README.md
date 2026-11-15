# Sprints AI Career & Assessment Orchestrator

**Submission verdict: NOT READY.** This is the existing LangGraph solution with focused security corrections and honest offline evidence. Actual isolated Python execution is now verified for the stated local cases. Paid OpenAI inference and a genuine 3-5 minute demo recording remain pending. Cold retrieval also misses the 1000 ms target in part of the sample.

The application uses real LangGraph, MemorySaver, ChromaDB and SQLite. Default language decisions use **HeuristicReasoner** and **ScriptedChatModel**, with deterministic hashing embeddings. Mock model tests and execution fixtures are labeled. No paid API call, key reuse, GitHub push or external sharing occurred.

## Reproduce on Windows

Verified runtime: Windows, CPython 3.13. The audit used a fresh isolated `.venv-audit`. Other host OS/Python combinations have not been independently reproduced.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python -m pip check
python -m src.main build-db
python -m src.main ingest
python -m src.main sandbox-status
python -m src.main demo --verbose
python -m pytest --junitxml=evidence/tests.xml -rs
python scripts/benchmark_rag.py
python scripts/execute_notebook.py
```

On Linux, activate with `source .venv/bin/activate`. A Linux host reproduction remains unverified. `build-db` deliberately rebuilds the local derived SQLite file; the original bytes are preserved in the baseline evidence. Use `SPRINTS_DB_PATH` to direct a rebuild to a different local file.

The default demo **leaves every tier-1 placement pending**. `python -m src.main review-demo` requires a real terminal and explicit APPROVE or REJECT input with a rationale. Noninteractive invocation refuses review. No automatic approval switches exist.

## Evidence and deliverables

- [Demonstration preparation report](docs/audit/demo_readiness.md): current startup gate, supported-model preflight and refreshed artifacts.
- [Current readiness report](docs/audit/readiness_followup.md): complete follow-up results, latency distributions, deliverable status and rubric risks.
- [Current requirements matrix](docs/audit/requirements_matrix_followup.md) and [integration summary](docs/audit/integration_evidence_followup.md).
- [Executed container-backed evaluation notebook](notebooks/evaluator_optimizer_verified.ipynb): actual Linux execution with deterministic judge and explicitly labeled grader fault injection.
- [Follow-up test logs](evidence/followup_20261115/verified_pid/full_tests.xml), [kernel controls](evidence/followup_20261115/verified_pid/sandbox_controls.json) and [raw retrieval samples](evidence/followup_20261115/rag_latency.json).

Earlier snapshots remain available:

- [Requirement-by-requirement baseline and final audit](docs/audit/requirements_matrix.md): all 10 functional requirements, all 5 acceptance criteria, deliverables, discovery, source limitations and the weighted rubric estimate.
- [Final submission summary](docs/audit/submission_summary.md): requested A-L results and exact paths.
- [Updated technical report](submission/technical_report_current.pdf); original report remains preserved.
- [Updated stakeholder PPTX](submission/stakeholder_presentation_current.pptx) and [PDF](submission/stakeholder_presentation_current.pdf): 10 slides. Original versions remain preserved.
- [Executed evaluator-optimizer notebook](notebooks/evaluator_optimizer_loop.ipynb): actual safe fallback plus explicitly labeled execution fixtures.
- [Real end-to-end evidence](evidence/evaluation/scenarios.json) and [command outputs and exit codes](evidence/commands).
- [Raw cold and warm latency samples](evidence/benchmark/rag_latency.json).
- [Video script and recording checklist](docs/demo_recording_script.md): **video PENDING**. A script or console transcript is not a recording.
- [Working client references](_client_sources/README.md): original kickoff PPTX and discovery MP3 are unavailable.

The preserved follow-up full suite reports **157 passed, 0 failed, 0 skipped**, including all 14 sandbox categories and two additional actual-container regressions. The current startup/model preparation changes have **70 focused passing tests**, exit0; the full expensive security suite was not repeated. The PID probe was changed from repeated interpreter launches to direct fork attempts that require the 32-task cgroup limit and an increased limit-hit counter; the five-second execution deadline is unchanged. The earlier 105-pass/14-skip run and subsequent failed runs are preserved, with the reason for each correction in the current readiness report. The original Windows suite could not collect (exit 4, missing `resource`); original code and tests remain in [the baseline snapshot](evidence/baseline/original_source.zip).

## Architecture and security

The [typed graph state](src/state.py) routes curriculum questions to Advisor RAG, placement requests to scoped SQL and code submissions to Assessor. It uses bounded RAG critique/reformulation and at most three grading refinements. [Architecture diagram source](docs/architecture.mmd).

[OrchestratorService](src/service.py) is the learner-facing API. Trusted local bootstrap issues opaque mock sessions; callers submit strict text requests. The service allocates opaque owned threads and withholds raw checkpoint state. Each database tool independently checks learner scope. Arbitrary SQL is disabled.

Tier-1 review uses LangGraph interrupt, strict Pydantic decisions, a scoped trusted reviewer context, a hash of the pending action and atomic one-time consumption. Rejection withholds the draft; replay, forged metadata and cross-learner requests are denied. Tests prove these POC transitions using mock reviewer sessions, not real identity verification.

See the [security model](docs/security_model.md) for trust boundaries and production gaps. Mock session issuance is an application-bootstrap fixture, never a public username-only login endpoint. MemorySaver, identity, review registries and audit events are process-local.

## Python sandbox

The old POSIX host executor has been replaced with a **container-only** backend. No learner snippet runs on the host. If the local Linux Docker daemon, required controls or approved immutable image is unavailable, the result is structured **Unable to verify** with no grade.

The intended policy includes network none, UID/GID 65534, read-only root, no host mounts, clean environment/config, seccomp, dropped capabilities, no-new-privileges, 512 MiB RAM/no swap, half CPU, pids 32, CPU/file/core/descriptor limits, a bounded temporary filesystem, capped stdout/stderr, execution deadline and mandatory per-submission cleanup.

To enable it, a trusted operator must provision an approved minimal Linux Python image and set `SPRINTS_SANDBOX_IMAGE` to its exact local `sha256:<64 hex>` image ID. No pull occurs during submissions. [Dockerfile](sandbox/Dockerfile) requires an approved digest-pinned base argument. The normal CLI now prepares Chroma and exposes READY only after a real collection query and graph construction succeed. Failed preparation returns UNAVAILABLE and exits2. [Operational latency contract](docs/rag_readiness.md). Then run:

```powershell
python -m src.main readiness
python -m src.main sandbox-status
python -m pytest -m sandbox_integration -rs
```

**Current host result: Docker Desktop Linux/WSL2 is available.** Normal authorized execution reaches its local daemon; the restricted session cannot access the pipe. A dedicated image was built from a digest-pinned official Python base. Actual inspection and kernel execution verify the listed controls for this local setup. Static screening and mock transport tests remain separate evidence. Trusted startup has a bounded eight-second readiness handshake before submission delivery; learner execution remains limited to five seconds. The runner's grading harness shares the submitted interpreter; verdict integrity after a Python restriction escape remains a separate limitation. Stronger production isolation and separate trusted grading are recommended.

## Data and measurements

The supplied learner CSV has **25 unchanged records**. The local SQLite materialization includes those learners and **16 synthetic openings**. All six curriculum documents are synthetic POC content. No additional learner rows were generated. The attributed 500-learner kickoff claim cannot be independently checked without the original deck. [Data provenance](docs/data_provenance.md).

Exact cl100k_base ingestion produces 8 chunks, maximum 500 tokens, with 50 token positions of overlap. Missing exact tokenization fails explicitly. The [follow-up benchmark](evidence/followup_20261115/rag_latency.json) reports n, p50, p95, p99, max and threshold compliance for process startup, cold retrieval, readiness and warm queries. Cold first retrieval p95 is 1591.568 ms (n=20, 85% below 1000 ms). First retrieval after successful startup preparation has p95 13.129 ms (n=20, 100% below 1000 ms); warm p95 is 16.128 ms (n=200, 100% below 1000 ms). All slow samples are retained. Cold acceptance remains partial; readiness is not a demonstrated cold-query speedup. These are observed results, not universal guarantees.

The discovery target is **80% less student waiting**. No business baseline or pilot events exist, so achieved reduction is **NOT VERIFIED**. Retrieval latency does not substitute for queue waiting. [Measurement methodology](docs/business_metrics.md).

## OpenAI verification boundary

Do not enable paid adapters before explicit authorization. The code blocks provider creation by default with `SPRINTS_LIVE_AUTHORIZED=0`. No existing credential was inspected. [Controlled live verification plan](docs/live_verification_plan.md) defines the model, request/token budget, timeout, retry policy, estimated cost and evidence. The prepared default is gpt-6-luna with reasoning_effort=none for Chat Completions function tools. Project access/quota and live behavior are unverified. A current operator preflight and separate approval are mandatory. There is no silent provider/model substitution.

## Submission

The final ZIP, external audit manifest and checksums live in `submission/`. They are preserved earlier snapshots and exclude the follow-up changes. The refreshed report/deck are separate current files; the preserved ZIP still contains the earlier versions. The ZIP has intentionally not been overwritten. Environments, caches, credentials and intermediate build files are excluded. A clean extraction is checked separately. No publication or external sharing is authorized by these local artifacts.
