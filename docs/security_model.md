# POC security boundary

## Trusted application identity

MockIdentityProvider issues opaque random sessions during local application bootstrap. Account provisioning and role assignment are trusted operator actions. This simulates authenticated context; it is not a password login, SSO integration or production identity proof. Do not expose mock session issuance as a learner-facing endpoint.

OrchestratorService accepts strict learner requests containing text and an optional assignment hint. It allocates opaque threads and owns the private graph/checkpointer. Learners cannot supply learner_id, thread_id, messages, approval, code or profile state. Every database tool independently checks a ContextVar-bound trusted learner context. Tools use parameterized, allowlisted operations; arbitrary SQL remains disabled even for authenticated sessions.

Python underscore/private attributes are an application API boundary, not protection against hostile Python running in the host process. A hostile user with filesystem/process access can bypass this POC. Learner code therefore never runs in that process.

## Human review

Tier-1 drafts pause at LangGraph interrupt. Public learner responses and snapshots omit profiles, raw messages, drafts and tool results. A scoped application-issued reviewer session must send strict Pydantic boolean approval, pending ID and nonempty rationale. The service hashes the complete structured recommendation, validates the current pending checkpoint, binds trusted reviewer context, consumes the review atomically, then resumes. A lock serializes conflicting decisions. Forged reviewer strings, replay, wrong pending IDs and learner attempts are denied.

Rejection closes the pending action and releases no tier-1 draft. Resume failures fail closed and require operator recovery. Audit events store timestamp, random pending ID, action and actor role only. Normal demo never approves tier-1; the separate interactive review command requires explicit operator input. Automated approval/rejection tests use declared mock actors and are not evidence of a real human review.

## Python execution

Only a restricted local Linux Docker backend may execute submitted code. It uses an immutable approved local image ID with pull disabled, a credential-free CLI config and explicit local socket/pipe, network none, UID/GID 65534, read-only root, no host mounts, default seccomp, all capabilities dropped, no-new-privileges, 512 MiB RAM/no swap, half CPU, pids 32, CPU/file/core/descriptor limits, a bounded temporary filesystem, a 5 s execution deadline and capped stdout/stderr. Trusted container startup is bounded to eight seconds and must signal readiness before learner input is sent. The learner execution deadline remains five seconds. A 512 MiB address-space limit supplements the cgroup memory cap. Every submission has its own container name; cleanup is mandatory. Input uses a bounded UTF-8 frame rather than waiting for stdin EOF; missing or malformed grading verdicts return Unable to verify. A delayed attach command is accepted only when daemon timestamps prove an exit0, non-OOM container completed within the whole-container time budget, with complete I/O and cleanup.

AST screening and restricted builtins are additional controls. They are not the containment boundary. The trusted harness shares a Python interpreter with the submission, so sophisticated grading-verdict forgery after a language-policy escape remains a limitation even if kernel containment passes. For production, separate grading orchestration from the untrusted interpreter and assess a stronger sandbox such as gVisor or a microVM.

The earlier audit could not access the daemon from its restricted session. The follow-up read-only probe established that Docker Desktop Linux/WSL2 is running and reachable from the normal execution context. A dedicated digest-pinned Python image was built, and actual container inspection plus a kernel probe verified UID/GID65534, CapEff=0, NoNewPrivs=1, Seccomp=2, memory.max=512 MiB, memory.swap.max=0, pids.max=32 and cpu.max=50000/100000. See evidence/followup_20261115/verified_pid/sandbox_controls.json and the latest requirements/readiness addendum for exact test counts, including preserved earlier failures. Static policy rejection and mocked transport cases remain separately labeled; they are not kernel evidence. The application returns a structured fallback and issues no grade when containment is unavailable. No host Python fallback exists.

## Persistence and operational limits

MemorySaver, session registry, review registry, audit events and locks are process-local. Restart loses pending review capabilities; production needs durable transactional ownership and audit storage. There is no deployment, rate limiter, identity provider or production credential vault in this POC. Retrieval timeouts cannot forcibly cancel a running Chroma call in a worker thread; only two workers execute concurrently, and startup warm-up is separate from the measured cold path.

Docker policy references: [running containers](https://docs.docker.com/engine/containers/run/), [resource controls](https://docs.docker.com/engine/containers/resource_constraints/). These document intended controls; the runtime results must establish whether the host actually enforces them.
