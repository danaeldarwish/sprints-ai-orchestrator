# Controlled OpenAI verification plan - NOT EXECUTED

Explicit user authorization is required before any key is read or any paid request is sent. No existing key was inspected or reused. No provider substitution is allowed.

Provider: OpenAI API, retaining the existing adapter. Proposed exact model: `gpt-4o-mini-2024-07-18` (existing configuration uses its alias `gpt-4o-mini`). Official documentation, checked 2026-11-15, marks this model deprecated. Deprecation is not proof of account access or successful inference. Confirm availability after authorization; stop if unavailable. Do not silently switch models.

## Envelope

- At most 12 HTTP chat requests total, counting parser repair attempts and any failed HTTP attempts.
- At most 4,000 input tokens and 500 output tokens per request. Reject larger requests rather than truncate required evidence.
- Client timeout: 20 seconds per HTTP request. SDK HTTP retries: 0.
- Structured parser may attempt a second request on malformed JSON; this consumes the same total budget.
- On 429, authentication failure, model-not-found, timeout, or budget exhaustion: stop; preserve the failure and offline evidence. No automatic alternate-provider or alternate-model fallback.
- Proposed spend ceiling: USD 0.05. At the model page's displayed USD 0.15 / million input and USD 0.60 / million output tokens, 48,000 input + 6,000 output tokens estimate USD 0.0108. This is a planning estimate, not actual spend. Recheck pricing immediately before approval.
- Use local hashing embeddings for this small inference verification; paid embeddings are outside this request envelope and remain unverified. A separate embedding budget would require approval.

## Cases and evidence

1. One intent decision; verify strict structured intent.
2. Actual local Chroma context sufficiency, reformulation when needed, and an attributed answer.
3. One assessment and judge result using genuinely isolated execution evidence only after sandbox integration passes. If the sandbox is unavailable, stop this case and record Unable to verify; never relabel fixtures as execution.
4. A tool-calling career lookup using scoped SQLite tools; verify row-derived recommendation and pending HITL. Reserve remaining calls for parser repair within the ceiling.

Before enabling the existing adapter, implement or attach a request-level shared counter/token guard across all model instances. The present graph caps refinements, but that is not a global paid-request budget. Running the unrestricted full demo is not this controlled plan.

Capture UTC timestamps, exact provider/model ID, SDK versions, sanitized case ID, prompt-template version/hash, retrieved source IDs, response/request ID, per-request latency, token usage, finish reason, parsed schema result, tool names/status, and exception class/status. Store raw text only if it contains no private learner records. Never store Authorization headers, keys, bearer sessions, or full environment/config dumps.

## Sources

- [OpenAI model documentation](https://developers.openai.com/api/docs/models/gpt-4o-mini) - model status and displayed token prices.
- [OpenAI pricing](https://developers.openai.com/api/docs/pricing) - current pricing should be rechecked before execution.
- [OpenAI deprecations](https://developers.openai.com/api/docs/deprecations) - lifecycle check.

Actual calls made during this audit: **0**. Actual API spend from this audit: **0**. No live inference claim is made.
