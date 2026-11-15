# Reproduce the offline submission

Use the extracted `sprints-ai-orchestrator` folder as the working directory. Verified host: Windows and CPython 3.13. A fresh dependency installation and a second host reproduction were not repeated during final packaging. The final receipt distinguishes extracted-source execution using the existing audit environment from a fresh installation.

## Environment and separate data paths

```powershell
python -m venv .venv
$pythonDemo = '.\.venv\Scripts\python.exe'
& $pythonDemo -m pip install -r requirements-lock.txt
& $pythonDemo -m pip check
$demoRoot = Join-Path $PWD ('.build/demo-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $demoRoot -Force | Out-Null
$env:SPRINTS_DB_PATH = Join-Path $demoRoot 'learners.db'
$env:SPRINTS_CHROMA_DIR = Join-Path $demoRoot 'chroma'
$env:SPRINTS_LLM = 'offline'
$env:SPRINTS_EMBEDDINGS = 'hashing'
$env:SPRINTS_LIVE_AUTHORIZED = '0'
$env:ANONYMIZED_TELEMETRY = 'False'
$env:LANGSMITH_TRACING = 'false'
$env:LANGCHAIN_TRACING_V2 = 'false'
& $pythonDemo -m src.main build-db
if ($LASTEXITCODE -ne 0) { throw 'Database preparation failed.' }
& $pythonDemo -m src.main ingest
if ($LASTEXITCODE -ne 0) { throw 'Curriculum ingestion failed.' }
```

These paths preserve the supplied SQLite bytes. No credentials or `.env` file are needed. `requirements-artifacts.txt` is only needed to rebuild documents; the PDF and ten-slide PPTX/PDF are supplied.

## Docker image

Start your existing Docker Desktop Linux engine normally. Do not change its security settings. If the preserved image ID is locally present, use it after inspection. On another machine, build the same pinned recipe and derive that machine's actual local image ID. Pulling/building is a setup step, never part of learner execution:

```powershell
$sandboxReceipt = Get-Content -Raw 'evidence/followup_20261115/sandbox_image.json' | ConvertFrom-Json
$base = $sandboxReceipt.pinned_base
docker pull $base
if ($LASTEXITCODE -ne 0) { throw 'Pinned base unavailable.' }
docker build --network none --pull=false --build-arg "PYTHON_BASE=$base" --tag sprints-grading-sandbox:verified --file sandbox/Dockerfile sandbox
if ($LASTEXITCODE -ne 0) { throw 'Sandbox image build failed.' }
docker image inspect sprints-grading-sandbox:verified
$imageId = docker image inspect --format '{{.Id}}' sprints-grading-sandbox:verified
if ($LASTEXITCODE -ne 0 -or $imageId -notmatch '^sha256:[0-9a-f]{64}$') { throw 'Invalid image ID.' }
$env:SPRINTS_SANDBOX_IMAGE = $imageId.Trim()
& $pythonDemo -m src.main sandbox-status
& $pythonDemo -m src.main readiness
if ($LASTEXITCODE -ne 0) { throw 'Application unavailable.' }
```

Require sandbox `available=true` and application `READY`, `accepting_learner_requests=true`. Stop if either fails. No host execution fallback is permitted. The pinned image is not embedded in the ZIP. `scripts/prepare_sandbox_image.py` is the original host-specific audit helper; the commands above are the portable equivalent and do not overwrite its historical receipts.

## Demonstration and checks

```powershell
& $pythonDemo -m src.main demo --verbose
& $pythonDemo -m src.main review-demo
# Human types APPROVE and a rationale in this terminal.
& $pythonDemo -m src.main review-demo
# Human types REJECT and a rationale for this fresh proposal.
```

The normal demo must show attributed curriculum retrieval, actual grades 60/100 FAIL and 100/100 PASS, SQLite matching, pending tier-1 review and cross-learner denial. A zero CLI exit alone does not prove that the sandbox returned grades; inspect the structured results. No scripted review input is acceptable as human evidence.

The executed notebook is `notebooks/evaluator_optimizer_verified.ipynb`: four executed code cells, actual container grading, explicitly injected grader faults and a deterministic judge. Live LLM-as-Judge behavior remains unexecuted. The original `evaluator_optimizer_loop.ipynb` preserves earlier fallback/fixture evidence.

For fresh tests, use a new output path to preserve earlier evidence:

```powershell
$checkRoot = Join-Path $PWD ('.build/check-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $checkRoot -Force | Out-Null
& $pythonDemo -m pytest -q -p no:cacheprovider --junitxml="$checkRoot/tests.xml"
```

Recording instructions and the planned 4:30 sequence are in [demo_recording_script.md](demo_recording_script.md). Cold retrieval remains partial. The 80% waiting-time reduction is unmeasured. No paid API calls, GitHub publication or platform submission are part of these commands.
