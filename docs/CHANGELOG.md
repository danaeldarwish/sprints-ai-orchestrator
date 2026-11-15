# Remediation - 15 November 2026

- Preserved original ZIP/source/tests and data hashes.
- Replaced host execution with a required restricted Linux container, explicit host-runner refusal and fail-closed behavior. Actual containment remains unverified on this host.
- Added trusted mock identity context, learner-scoped SQL and checkpoint ownership, strict bound one-time review, replay/race rejection and metadata-only logs.
- Removed noninteractive tier-1 auto approval and approximate token-count fallback. Added exact token windows, raw cold/warm benchmarks and evidence labels.
- Executed isolated offline regressions and notebook; created report/deck, recording plan, working references and final-package audit. No paid calls or publication.

## Historical submitted decision log

The entries below came from the original ZIP. Their historical execution claims are not independently verified. In particular, entry 1 mentions local audio transcription, but the audio, transcription process and original media are unavailable in this audit. Entry 5 describes the superseded executor and must not be treated as the current security design.

# Decision log
| # | Decision | Why |
|---|---|---|
| 1 | Transcribed the discovery call locally (Whisper small.en via sherpa-onnx) | Call holds requirements the brief omits (80% goal, sandbox, hallucination fear, live demo) |
| 2 | Provider-agnostic `Reasoner` interface; offline heuristic backend + OpenAI backend | Build environment had no LLM access; graph and tools are identical in both modes |
| 3 | Hashing embedder for offline use | Hosted embedding models unreachable; deterministic and fast; OpenAI embeddings switchable |
| 4 | Career messages rendered from DB rows, then grounding-checked | Client's biggest fear is invented qualifications |
| 5 | Custom sandbox (AST + subprocess + rlimits) instead of bare `PythonREPL` | Brief says "securely"; the stock REPL is unsandboxed |
| 6 | Test harness nonce | A submission could print a fake passing result |
| 7 | Eligibility = track, preferred employer, modules, score, readiness, salary band | Derived from the DB columns supplied; documented in the career policy |
| 8 | Sufficiency check by query-term coverage; reformulation via curriculum glossary (offline) | Deterministic stand-in for LLM reflection; LLM prompts provided |
| 9 | Refinement cap = 3 refinements (4 grader calls) | Literal reading of "max 3 refinement iterations" |
| 10 | Bug found by tests: vague follow-up erased `last_topic` | Fixed: keep prior topic when new turn has none |
| 11 | Notebook exposed that an unapproved grade was shown as final | Now shown as provisional, no pass/fail, flagged for human grader |
| 12 | Reformulate loop ran a 4th search after giving up | Added conditional edge after reformulate |
