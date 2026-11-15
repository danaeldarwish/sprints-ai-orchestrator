# Genuine demo recording — VIDEO STATUS: PENDING

Windows Snipping Tool was found in the installed-app inventory on 15 November 2026. Its launch returned “Computer Use app approval timed out”; the Record control was not inspected and capture did not start. OBS and Free Cam were not found at their standard install paths; FFmpeg/FFprobe were not on PATH. No capture installation or permission changes were attempted. No recording has been fabricated, and no MP4 or recording link exists. The sequence below is a recording plan, not measured video duration. The available demonstration is **offline language reasoning with actual LangGraph, ChromaDB, SQLite and Linux container execution**. Live OpenAI inference remains a separate approval gate.

## Prepare before starting capture

Open a normal local PowerShell terminal in the project root. The restricted agent session cannot open Docker's pipe; the verified normal-user execution context can. Do not change Docker settings or run grading on Windows as a fallback.

~~~powershell
$pythonAudit = if (Test-Path '.\.venv-audit\Scripts\python.exe') { '.\.venv-audit\Scripts\python.exe' } else { '.\.venv\Scripts\python.exe' }
$demoRoot = Join-Path $PWD ('.build/demo-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $demoRoot -Force | Out-Null
$env:SPRINTS_DB_PATH = Join-Path $demoRoot 'learners.db'
$env:SPRINTS_CHROMA_DIR = Join-Path $demoRoot 'chroma'
$env:SPRINTS_LLM = 'offline'
$env:SPRINTS_EMBEDDINGS = 'hashing'
$env:SPRINTS_LIVE_AUTHORIZED = '0'
$sandboxReceipt = Get-Content -Raw 'evidence/followup_20261115/sandbox_image.json' | ConvertFrom-Json
$env:SPRINTS_SANDBOX_IMAGE = $sandboxReceipt.image.id
& $pythonAudit -m src.main build-db
if ($LASTEXITCODE -ne 0) { throw 'Database preparation failed.' }
& $pythonAudit -m src.main ingest
if ($LASTEXITCODE -ne 0) { throw 'Curriculum ingestion failed.' }
& $pythonAudit -m src.main readiness
if ($LASTEXITCODE -ne 0) { throw "Application is unavailable; do not begin capture." }
& $pythonAudit -m src.main sandbox-status
~~~

Require READY with accepting_learner_requests=true and sandbox available=true before recording. Readiness includes real Chroma preparation and is not part of the prepared query budget. Review the preserved 157-pass suite and the new focused startup/model checks. If the image is absent on another machine, use the pinned base/build recipe in scripts/prepare_sandbox_image.py and inspect the resulting local image; do not disable required controls. The demo paths above preserve the supplied SQLite bytes. Review the latest full tests before capture; earlier failed runs are retained as well.

## Planned 4 minute 30 second walkthrough

| Time | On-screen action and narration |
|---|---|
| 0:00–0:25 | State the project goal and the offline mode. Real tools and execution; deterministic reasoner/judge; mock identities; synthetic curriculum/openings. Describe 80% waiting reduction as an unmeasured target. |
| 0:25–0:45 | Show sandbox-status and the actual kernel/control receipt in evidence/followup_20261115/verified_pid/sandbox_controls.json. Explain UID65534, no network/mounts, read-only root, resource limits and mandatory cleanup. |
| 0:45–2:20 | Run the command below. Curriculum scene shows a learner question, retrieved source filenames and graph reflection. Buggy/corrected submissions show actual container grading and score/feedback_points/pass_status. Career scene shows database-backed modules, score, EGP target and opening band. Fawry remains pending. Keep the real output visible and scroll; do not replace slow runs with invented outputs. |
| 2:20–3:05 | Run review-demo. Show the learner's withheld pending response, then the reviewer draft. As the explicitly identified local mock reviewer type APPROVE and a rationale. Show released recommendation and audit action. |
| 3:05–3:45 | Run review-demo again for a fresh proposal; type REJECT and a rationale. Show rejection and withheld placement. Explain production identity is not implemented and no external placement is performed. |
| 3:45–4:10 | Open notebooks/evaluator_optimizer_verified.ipynb and show the preserved executed outputs: real container results, one-refinement grader fault injection, and the three-refinement cap. Label the fault-injected grader and deterministic judge accurately. Show isolation/replay test results. |
| 4:10–4:30 | Show the benchmark and docs/audit/demo_readiness.md. Distinguish cold, startup preparation and warm queries. State paid inference and recording/publication gates honestly. |

~~~powershell
& $pythonAudit -m src.main demo --verbose
& $pythonAudit -m src.main review-demo
# Enter APPROVE, then a review rationale.
& $pythonAudit -m src.main review-demo
# Enter REJECT, then a review rationale.
~~~

review-demo requires an actual TTY and explicit human input. Never use a pipe, scripted response or automated regression fixture as evidence of a human decision. The default demo has no auto-approve switch. No reviewer bearer token is printed.

## Actual capture and validation

Manually open Windows Snipping Tool from Start. If a Record/video control is present, select it, choose New, drag around only the terminal/notebook area, review microphone/system-audio controls, and press Start. The person recording must grant any capture/audio permission themselves. If this installed version offers only screenshots, use an already installed recorder you trust or obtain a recording tool separately; do not treat a screenshot as a video. OBS is an alternative if already available. Use 1920×1080 or 1280×720, readable terminal zoom, and only the relevant windows. Keep credentials and unrelated windows out of view. Start from a clean terminal without credential commands in its scrollback.

Save the genuine local file as submission/demo_walkthrough.mp4. Play the entire file, confirm readable output and narration, and inspect Properties > Details for **180–300 seconds**. Record its actual duration, size and SHA256 using Get-FileHash. A planned 4:30 sequence is not proof of duration. If it exceeds five minutes, repeat the real walkthrough; do not claim a nonexistent compliant video. Publishing/uploading still requires authorization.

After playback, record actual properties and checksum in a new evidence file. Example commands, only once the real file exists:

~~~powershell
$videoPath = Join-Path $PWD 'submission/demo_walkthrough.mp4'
Get-Item -LiteralPath $videoPath | Select-Object FullName,Length
Get-FileHash -LiteralPath $videoPath -Algorithm SHA256
# Read actual duration from Properties > Details and record it with the playback check.
~~~

Expected local capture path: C:\Users\sh\OneDrive\Documents\sprint1_gp\sprints-ai-orchestrator\sprints-ai-orchestrator\submission\demo_walkthrough.mp4. This is a requested output path, not an existing recording.

Only after the actual file is reviewed should VIDEO STATUS become complete and a new versioned package be built. Until then it remains **PENDING**.

## Demonstration checklist

- Confirm the interpreter, local image ID, separate demo DB/Chroma paths and offline flags before capture.
- Show READY before the first learner input; stop if initialization or sandbox availability fails.
- Show cited curriculum sources; label heuristic critique and local hashing.
- Show real-container buggy/corrected feedback with score, feedback_points and pass_status; label the deterministic judge and actual refinement count.
- Show stored modules/score, target salary in EGP, employer preference and row-derived opening. Openings are synthetic POC records.
- Keep Fawry pending in the default demo. Perform explicit APPROVE and rationale only in a real reviewer terminal; separately demonstrate REJECT for a fresh pending action. No scripted approval is allowed.
- Show the existing actual-container optimizer notebook, including labeled injected grader faults; do not describe its outputs as paid inference.
- State cold retrieval remains partial, production identity/storage are absent, and 80% waiting reduction is unmeasured.
- Play the entire genuine recording, verify 180-300 seconds and readable output, record actual duration/size/SHA256. Until then VIDEO STATUS=PENDING.
