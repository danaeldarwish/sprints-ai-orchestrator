# Final readiness follow-up — NOT READY

Current addendum; earlier report/slides/ZIP remain unchanged. No publication/submission or paid inference occurred.

## A. Docker

Docker Desktop 4.97.0/Engine 29.9.2, Linux amd64/WSL2. Context desktop-linux; Ubuntu/docker-desktop running. Restricted-session pipe/WSL access is denied; normal execution outside that restriction succeeds. No reinstall/restart/reconfiguration. A public official Python base was resolved to a digest and used for a dedicated minimal image with an empty Docker CLI config.

## B. Tests

**157 passed, 0 failed, 0 errors, 0 skipped.** Sandbox categories: 14/14 passed, including the corrected PID probe. Additional EOF-open/raw-stderr cases: 2/2 passed. [JUnit](../../evidence/followup_20261115/verified_pid/full_tests.xml).

Earlier runs remain: initial14 skipped due to CPU JSON field mismatch; selected 10 passed / 4 failed; pre-framing full 137 passed / 4 failed; framed full 143 passed / 4 failed. Eight additional print-only probes did not reproduce the intermittent failure. LF framing removes EOF dependence. Delayed attach recovery accepts only exit 0 with valid daemon timestamps proving whole-container lifetime within budget; signal exits/unknown/over-budget state remain failures. The exit-proof run retained 149 passed / 3 failed; the readiness run retained 156 passed / 1 failed. Its last PID probe launched repeated Python interpreters and spent 8.125 s including cleanup; it correctly remained a timeout. The preserved original probe was replaced by 64 direct fork attempts that require pids.max=32, current=32, EAGAIN and an increased pids.events max counter, with all children reaped before success. The five-second deadline and 32-task cap are unchanged. No claim that every historical timeout has a proven cause.

## C. Security

Actual inspection/kernel probe confirms UID/GID 65534, CapEff 0, NoNewPrivs 1, Seccomp 2, network none, read-only root, no host mounts, memory 512 MiB / swap 0, processes 32 and CPU 0.5. File/descriptor/core limits, bounded tmpfs/output/input and mandatory cleanup remain. Trusted startup has an eight-second bounded handshake before learner input is sent; the five-second submission deadline is unchanged. A 512 MiB RLIMIT_AS supplements cgroup memory limits. Missing/malformed input or grading verdicts return Unable to verify. [Kernel/control receipt](../../evidence/followup_20261115/verified_pid/sandbox_controls.json).

Residual risks: shared Linux kernel/daemon trust, same-interpreter grading-verdict integrity after restriction escape, mock identity and process-local ownership/checkpoints/reviews/audit. Broad concurrency/load reliability is not certified. Static AST rejection is not kernel evidence. Learner code never executes on Windows.

## D. RAG benchmark

| Measurement | n | p50 ms | p95 ms | p99 ms | max ms | under 1000 |
|---|---:|---:|---:|---:|---:|---:|
| Process start/query/exit | 20 | 9307.468 | 14760.504 | 15508.491 | 15508.491 | 0.0% |
| Unprepared first retrieval | 20 | 483.953 | 1591.568 | 1593.507 | 1593.507 | 85.0% |
| Startup preparation | 20 | 674.092 | 1913.966 | 3216.537 | 3216.537 | 65.0% |
| First query after readiness | 20 | 8.48 | 13.129 | 36.962 | 36.962 | 100.0% |
| Warm | 200 | 8.338 | 16.128 | 36.929 | 65.852 | 100.0% |

Nearest-rank, 20 alternating fresh-process pairs and 200 warm queries; same eight-chunk persisted synthetic corpus, actual Chroma/local hashing. OS cache not flushed; desktop load uncontrolled. All outliers retained, 30 s observation window. Five relevance checks and source attribution passed. [Raw samples](../../evidence/followup_20261115/rag_latency.json).

Five-sample profiling attributed most cold query time to client/collection initialization; imports take additional seconds. No underlying cold-query speedup is demonstrated. Existing warm-up now fails explicitly if readiness fails. Only a missing collection triggers ingestion; operational errors no longer rebuild data. That error-branch-only change followed timing and is documented in benchmark_source_addendum.json. Cold acceptance stays PARTIAL.

## E. OpenAI plan

Exact gpt-4o-mini-2024-07-18; maximum 24 shared outbound attempts including repairs/failures; input admission 4000 tokens, output 500, timeout 20 s, SDK retries 0, at most two total parser attempts. Stop on provider error; no streaming/async/model fallback. Dedicated SPRINTS_VERIFICATION_API_KEY only; no ambient key/dotenv reuse. Local embeddings only. Nominal 17 calls for five actual graph cases; cap may leave partial coverage. Estimated token cost $0.0216 at checked prices, proposed ceiling $0.05. Deprecated model: recheck availability/pricing and stop if unavailable. **Actual paid requests 0.** [Reviewable plan](../live_verification_plan.md).

## F. Demo

**VIDEO STATUS=PENDING.** Planned 4:30 walkthrough covers actual curriculum sources, isolated grading/structured feedback, bounded optimizer, SQL progress/EGP/preferences, grounded matching, Fawry interrupt and explicit mock reviewer approval/rejection. Automatic video capture is unavailable. User must record/review a genuine 180–300 s file; scripted logs are not a video. [Precise instructions](../demo_recording_script.md).

## G. Deliverables

| Deliverable | Status |
|---|---|
| Local source/lock/image recipe | Present; scoped local reproduction |
| Shareable repository/workspace URL | Missing; no publication authorized |
| Executed evaluation notebook | New actual-container notebook plus preserved original |
| Supplied CSV/documented SQLite | Present; 25 learners/16 synthetic openings; original bytes checked |
| Technical report PDF | Present; 16 pages; preserved earlier snapshot |
| Stakeholder presentation | Present; 10 slides, PPTX/PDF; preserved earlier snapshot |
| Genuine video/link | Missing/PENDING |
| Final compressed package/manifest | Present but stale; intentionally not overwritten |

## H–I. Blockers and verdict

**NOT READY**. Cold retrieval still misses 1000 ms; real model/judge/tool behavior awaits separate approval; genuine video and shareable URL are missing. The latest offline suite has no failed or skipped tests. Refresh report/deck/package after these gates close. Original PPTX/MP3 and assignment-page fidelity remain unverified. 80% waiting reduction is a target; business timing observations=0.

| User-supplied rubric | Weight | Risk |
|---|---:|---|
| Functional completeness | 35 | Live LLM behavior and cold retrieval still partial; scoped Linux evidence now measured. |
| Quality and reproducibility | 20 | Earlier timeout failures retained; production identity/durability and broad load validation unresolved. |
| Integration across both sprints | 15 | Actual local integration; genuine LLM judge pending. |
| Technical report PDF | 10 | PDF exists as historical snapshot; refresh final results. |
| Stakeholder presentation | 10 | 10 slides exist as historical snapshot; refresh final results. |
| Recorded demonstration | 10 | No video; entire 10-point category at risk. |

Pass threshold 60/100 is from working notes. No official grade/guaranteed pass. Earlier 64/100 planning estimate is historical; no new score invented. Missing video risks all 10 recording points.

[Checked file existence/hashes and integration receipt](../../evidence/followup_20261115/integration_summary.json). Preserved final ZIP SHA256: b7bf8908db005675b4fa344b03f3037b8d8fc82586edaf1401e6ab6d3603c234.