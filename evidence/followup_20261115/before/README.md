# Sprints AI Career & Assessment Orchestrator

**Submission verdict: NOT READY.** This is the existing LangGraph solution with focused security corrections and honest offline evidence. Actual isolated Python execution, paid OpenAI inference and a genuine 3-5 minute demo recording remain unverified or pending. Cold retrieval also misses the 1000 ms target in part of the sample.

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

- [Requirement-by-requirement baseline and final audit](docs/audit/requirements_matrix.md): all 10 functional requirements, all 5 acceptance criteria, deliverables, discovery, source limitations and the weighted rubric estimate.
- [Final submission summary](docs/audit/submission_summary.md): requested A-L results and exact paths.
- [Technical report](submission/technical_report.pdf).
- [Stakeholder PPTX](submission/stakeholder_presentation.pptx) and [PDF](submission/stakeholder_presentation.pdf): 10 slides.
- [Executed evaluator-optimizer notebook](notebooks/evaluator_optimizer_loop.ipynb): actual safe fallback plus explicitly labeled execution fixtures.
- [Real end-to-end evidence](evidence/evaluation/scenarios.json) and [command outputs and exit codes](evidence/commands).
- [Raw cold and warm latency samples](evidence/benchmark/rag_latency.json).
- [Video script and recording checklist](docs/demo_recording_script.md): **video PENDING**. A script or console transcript is not a recording.
- [Working client references](_client_sources/README.md): original kickoff PPTX and discovery MP3 are unavailable.

The latest suite reports 105 passed and 14 skipped when the Linux sandbox is unavailable. Skips are actual containment/execution cases and are not passes. Read the current [JUnit evidence](evidence/tests.xml) and command JSON for authoritative counts. The original Windows suite could not collect (exit 4, missing `resource`); original code and tests remain in [the baseline snapshot](evidence/baseline/original_source.zip).

## Architecture and security

The [typed graph state](src/state.py) routes curriculum questions to Advisor RAG, placement requests to scoped SQL and code submissions to Assessor. It uses bounded RAG critique/reformulation and at most three grading refinements. [Architecture diagram source](docs/architecture.mmd).

[OrchestratorService](src/service.py) is the learner-facing API. Trusted local bootstrap issues opaque mock sessions; callers submit strict text requests. The service allocates opaque owned threads and withholds raw checkpoint state. Each database tool independently checks learner scope. Arbitrary SQL is disabled.

Tier-1 review uses LangGraph interrupt, strict Pydantic decisions, a scoped trusted reviewer context, a hash of the pending action and atomic one-time consumption. Rejection withholds the draft; replay, forged metadata and cross-learner requests are denied. Tests prove these POC transitions using mock reviewer sessions, not real identity verification.

See the [security model](docs/security_model.md) for trust boundaries and production gaps. Mock session issuance is an application-bootstrap fixture, never a public username-only login endpoint. MemorySaver, identity, review registries and audit events are process-local.

## Python sandbox

The old POSIX host executor has been replaced with a **container-only** backend. No learner snippet runs on the host. If the local Linux Docker daemon, required controls or approved immutable image is unavailable, the result is structured **Unable to verify** with no grade.

The intended policy includes network none, UID/GID 65534, read-only root, no host mounts, clean environment/config, seccomp, dropped capabilities, no-new-privileges, 512 MiB RAM/no swap, half CPU, pids 32, CPU/file/core/descriptor limits, a bounded temporary filesystem, capped stdout/stderr, execution deadline and mandatory per-submission cleanup.

To enable it, a trusted operator must provision an approved minimal Linux Python image and set `SPRINTS_SANDBOX_IMAGE` to its exact local `sha256:<64 hex>` image ID. No pull occurs during submissions. [Dockerfile](sandbox/Dockerfile) requires an approved digest-pinned base argument. Then run:

```powershell
python -m src.main sandbox-status
python -m pytest -m sandbox_integration -rs
```

**Current host result: local Linux Docker daemon unavailable.** Intended policy flags, static screening and mock transport results do not establish kernel containment. The runner's grading harness shares the submitted interpreter; verdict integrity after a Python restriction escape remains a separate limitation. Stronger production isolation and separate trusted grading are recommended.

## Data and measurements

The supplied learner CSV has **25 unchanged records**. The local SQLite materialization includes those learners and **16 synthetic openings**. All six curriculum documents are synthetic POC content. No additional learner rows were generated. The attributed 500-learner kickoff claim cannot be independently checked without the original deck. [Data provenance](docs/data_provenance.md).

Exact cl100k_base ingestion produces 8 chunks, maximum 500 tokens, with 50 token positions of overlap. Missing exact tokenization fails explicitly. The [benchmark](evidence/benchmark/rag_latency.json) reports n, p50, p95, p99, max and threshold compliance for cold process startup, cold first retrieval and warm queries. Warm p95 is 13.026 ms (n=200, 100% below 1000 ms); cold first-query p95 is 1202.391 ms (n=10, 90% below 1000 ms). These are this run's measured values, not universal guarantees.

The discovery target is **80% less student waiting**. No business baseline or pilot events exist, so achieved reduction is **NOT VERIFIED**. Retrieval latency does not substitute for queue waiting. [Measurement methodology](docs/business_metrics.md).

## OpenAI verification boundary

Do not enable paid adapters before explicit authorization. The code blocks provider creation by default with `SPRINTS_LIVE_AUTHORIZED=0`. No existing credential was inspected. [Controlled live verification plan](docs/live_verification_plan.md) defines the model, request/token budget, timeout, retry policy, estimated cost and evidence. The existing default model is deprecated and account availability is unverified. There is no silent provider/model substitution.

## Submission

The final ZIP, external audit manifest and checksums live in `submission/`. Environments, caches, credentials and intermediate build files are excluded. A clean extraction is checked separately. No publication or external sharing is authorized by these local artifacts.
