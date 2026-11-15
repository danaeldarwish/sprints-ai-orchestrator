# Controlled OpenAI verification — PREPARED, NOT EXECUTED

This follow-up replaces the earlier 12-request proposal with an executable five-case plan. Separate explicit user approval is still required. No provider credential was inspected or used, and actual paid requests/spend remain **0**.

## Exact proposed envelope

| Control | Value |
|---|---|
| Provider / endpoint | OpenAI Chat Completions, official HTTPS endpoint only |
| Exact model | gpt-4o-mini-2024-07-18 |
| Maximum outbound attempts | **24 total**, shared across every reasoner and SQL ReAct model instance |
| Input admission | Serialized messages, tool schemas and results, tokenized with cl100k_base, plus 1024-token safety allowance must fit 4000 tokens |
| Output / samples | 500 tokens maximum, n=1 |
| Timeout | 20 seconds per provider attempt |
| SDK HTTP retries | 0; redirects disabled |
| Parser repair | At most two total attempts; both consume the same shared 24-request budget |
| Failures | Any provider error latches the run stopped; no model/provider substitution |
| Other routes | Async and streaming disabled; only the two scoped SQLite function tools allowed |
| Embeddings | Local hashing only; paid embedding calls excluded |
| Estimated token cost | 24 × (4000 × $0.15 + 500 × $0.60) / 1,000,000 = **$0.0216** |
| Proposed spend ceiling | **$0.05**, subject to approval and pricing recheck |

The input check is conservative local admission, not an exact prediction of server billing. Actual token usage is recorded and an over-envelope response stops later requests. Output caps and request reservations are enforced before dispatch. Budgeted HTTP fixture tests exercise bound tools, repairs, errors, oversized inputs, output/model overrides and streaming rejection without network calls. The same-process Python implementation is not a security boundary against a developer intentionally replacing its client.

The official model page checked 2026-11-15 marks this snapshot **deprecated** and displays $0.15 input / $0.60 output per million tokens. Account availability is unknown. After approval, stop on model-unavailable/auth/rate-limit/timeout errors and report partial coverage. Do not choose a replacement automatically. Recheck price and lifecycle before execution.

## Five genuine runtime cases

1. Curriculum Q&A through the real graph with actual Chroma sources and LLM context/answer decisions.
2. Buggy Python submission: genuine restricted Linux execution, then Pydantic feedback.
3. Corrected Python submission: genuine execution and LLM judge/optimizer bounded to three refinements. Record actual refinement count; do not force or invent a rejection.
4. Non-tier-1 career lookup with real scoped SQLite tool calls, stored progress/EGP target/preferences and deterministic row-derived employer eligibility.
5. Fawry tier-1 lookup that remains at LangGraph interrupt. No automated human approval is included in this paid evaluation.

Nominal flow is about 17 requests if there are no repairs/retrieval retries/refinements. The hard cap may interrupt later cases; partial completion must remain partial. There is no reserved 24-request allowance per case.

## Credential setup and commands

The user provisions a dedicated restricted verification key into **SPRINTS_VERIFICATION_API_KEY** in the local execution process after approval. The adapter never loads dotenv files or borrows OPENAI_API_KEY from another project. Do not put keys in source, CLI arguments, chat, recordings or evidence. The child process receives only an allowlisted environment and the dedicated credential; Docker subprocesses receive no provider credentials.

Preparation is safe offline:

~~~powershell
.\.venv-audit\Scripts\python.exe scripts/verify_openai.py --plan
~~~

Only after the user separately approves the exact model, 24-request envelope and $0.05 ceiling, provision the credential privately and set SPRINTS_LIVE_AUTHORIZED=1, SPRINTS_OPENAI_MODEL=gpt-4o-mini-2024-07-18, and the locally verified SPRINTS_SANDBOX_IMAGE. Then execute:

~~~powershell
.\.venv-audit\Scripts\python.exe scripts/verify_openai.py --execute --approval-id USER_APPROVAL_REFERENCE --output evidence/live_NEW_TIMESTAMP
~~~

The output directory must be new. Missing sandbox, model mismatch, missing approval reference or missing dedicated credential stops execution. Running the unrestricted full demo is outside this approved envelope. Clear the dedicated credential from the process after the run.

## Evidence retained

The harness records UTC timestamps, exact/returned model, SDK versions, case status/schema, retrieved sources, sandbox image, prompt hashes, per-attempt latency, response/request IDs, finish reason, token usage and exception class/HTTP status. Raw prompts, bearer sessions, keys, request headers and full environment dumps are excluded. Outputs use the supplied local POC dataset; openings and curriculum are synthetic. A reviewer still checks answer quality and SQL/source grounding.

Implementation: src/live_controls.py, src/llm.py, scripts/verify_openai.py. Offline preparation receipt: evidence/followup_20261115/openai_plan.json. No live-results receipt exists yet.

Sources: [OpenAI model lifecycle and token pricing](https://developers.openai.com/api/docs/models/gpt-4o-mini), [pricing](https://developers.openai.com/api/docs/pricing), [deprecations](https://developers.openai.com/api/docs/deprecations).
