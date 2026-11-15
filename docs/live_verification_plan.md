# Supported-model verification - PREPARED, NOT EXECUTED

No OpenAI API request, including model-list/retrieve requests, was made. No credential was accessed. Public documentation was reviewed on15November2026. The former gpt-4o-mini-2024-07-18 has a published shutdown of14January2027. The recommended available catalog model is **gpt-6-luna**. The existing Chat Completions/SQL function-tool architecture can remain, with **reasoning_effort=none**, which is required for its Chat Completions function calling. Offline HTTP fixtures validate request serialization; real compatibility and project access remain unverified.

| Control | Proposed value |
|---|---|
| Model / endpoint | Exact gpt-6-luna; official Chat Completions HTTPS only; no substitution |
| Processing | Standard service_tier=default; global endpoint; reasoning_effort=none |
| Total completion attempts | **24 shared attempts**, including parser repairs and failed provider attempts |
| Input / output | Conservative admission **12000** tokens; output **500**, n=1 |
| Admission method | Larger of serialized local token count and UTF-8 bytes, plus1024; includes messages, tool schemas/results; may reject large cases |
| Timeout / SDK retries |20seconds / **0**; no redirects |
| Parser attempts | At most two total; same shared request/cost reservations |
| Other services | Local hashing embeddings; only two scoped SQLite function tools; no hosted tools, streaming or async |
| Ordinary token estimate |24x(12000x$0.10+500x$0.50)/1M = **$0.0348** |
| Conservative reservation | Cache-write input rate$0.125/M, output$0.50/M: **$0.00175 per attempt; $0.042 total** |
| Estimated-cost ceiling | **$0.05**; reserve before dispatch; consumed reservations are never refunded |

The byte guard is deliberately conservative and uses a larger envelope than the earlier4000-token proposal so actual curriculum context fits. An offline full-document stress fixture through the real answer template needed8904 bytes plus framing allowance. This is fixture sizing, not live model evidence. Estimates assume the checked prices and global Standard processing; the client is not a billing-system guarantee. Unexpected usage beyond the input/output envelope stops later dispatch.

Any authentication, rate-limit, quota, timeout or unexpected provider error latches the run stopped. Missing/invalid usage, exhausted cost/request budget or oversized input also stops it. No retries on provider errors, no model fallback. The model has only the published gpt-6-luna ID in the checked catalog; actual returned model and IDs must be retained to assess reproducibility.

## Project preflight - currently PENDING

1. Separately obtain the user's explicit approval for this exact model,24-attempt envelope and$0.05 estimated-cost ceiling.
2. In the intended OpenAI project, the operator must verify model entitlement, permission to use the supplied project data, billing/remaining quota and Standard global pricing. Public documentation does not prove these account facts. No account/API check has been executed here.
3. Copy docs/openai_preflight.template.json to .build/private/openai_preflight.json. Fill only verified boolean attestations and checked_at_utc. It must be current within24hours; changed prices stop execution pending a revised approved envelope. Keep credentials out of that JSON.
4. Privately provision a dedicated restricted verification key into SPRINTS_VERIFICATION_API_KEY for that process. Never borrow OPENAI_API_KEY, load unrelated dotenv files, put secrets in CLI arguments, recordings, source or logs.
5. Set the exact model, explicit authorization, local embeddings and verified image as below. Missing/incomplete preflight fails before credential access. Running commands below now is not authorized.

## Exact future execution command - NOT EXECUTED

Run in a private local terminal only after the separate approval and operator checks:

~~~powershell
$env:SPRINTS_LLM = 'openai'
$env:SPRINTS_EMBEDDINGS = 'hashing'
$env:SPRINTS_LIVE_AUTHORIZED = '1'
$env:SPRINTS_OPENAI_MODEL = 'gpt-6-luna'
$imageReceipt = Get-Content -Raw 'evidence/followup_20261115/sandbox_image.json' | ConvertFrom-Json
$env:SPRINTS_SANDBOX_IMAGE = $imageReceipt.image.id
# Provision SPRINTS_VERIFICATION_API_KEY privately in this process; never paste it into chat.
.\.venv-audit\Scripts\python.exe scripts/verify_openai.py --execute --approval-id APPROVAL_REFERENCE --preflight-file .build/private/openai_preflight.json --output evidence/live_NEW_TIMESTAMP
$liveExit = $LASTEXITCODE
Remove-Item Env:SPRINTS_VERIFICATION_API_KEY -ErrorAction SilentlyContinue
$env:SPRINTS_LIVE_AUTHORIZED = '0'
$env:SPRINTS_LLM = 'offline'
Write-Host "Verification exit code: $liveExit"
~~~

The output directory must be new. Record the actual process exit code and complete stdout/stderr locally. Do not claim exit0 or successful inference without inspecting live_results.json. Nonzero means failed or partial coverage. The safe offline preparation command is python scripts/verify_openai.py --plan --output evidence/NEW_DIRECTORY/openai_plan.json; it reads no key and preserves existing evidence.

## Five cases and evidence

Run sequentially: curriculum Q&A with actual Chroma sources; buggy Python grading in the verified container; corrected grading with actual LLM judge and at most3refinements; scoped SQLite career matching; Fawry paused at LangGraph interrupt. The paid evaluation never approves a placement. About17calls are nominal; repairs/retrieval retries can exhaust the shared cap and leave named cases unexecuted.

Collect UTC timestamps, exact requested/returned model, SDK versions, source IDs, sandbox image, public result/schema/status, prompt hashes, provider request/response IDs, finish reasons, input/output usage, reserved estimated cost, latencies, exception class/HTTP status, unexecuted cases and process exit code. Exclude raw keys, authorization headers, sessions and private prompt dumps. Human review of answer quality and row/source grounding is still required.

Sources: [Model and compatibility](https://developers.openai.com/api/docs/models/gpt-6-luna), [Current pricing](https://developers.openai.com/api/docs/pricing), [Deprecation schedule](https://developers.openai.com/api/docs/deprecations), [Migration compatibility](https://developers.openai.com/api/docs/guides/latest-model/gpt-6-astra.md#migration-quickstart).
