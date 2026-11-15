# GitHub preparation

Repository URL: **MISSING**. No remote was created, no upload was performed, and no publication is authorized. The working project currently has no Git metadata. The delivery packager creates a clean publish folder under `.build` with source, tests, notebook outputs, the supplied SQLite/CSV, documentation and preserved evidence. It excludes environments, caches, local charts, credentials and prior submission ZIPs. This is the folder to inspect and initialize.

The supplied learner data contains names, progress and salary preferences. Keep the repository private. Publishing even a private repository requires the user's explicit authorization. A static scan cannot prove that every possible secret is absent; the final validation receipt records the actual scan scope and findings.

## Exact local commands

Run these only after the final ZIP has been created. They select the newest delivery receipt and initialize its clean publish folder. These local commands do not create a remote or upload data.

```powershell
Set-Location 'C:\Users\sh\OneDrive\Documents\sprint1_gp\sprints-ai-orchestrator\sprints-ai-orchestrator'
$deliveryReceipt = Get-ChildItem -LiteralPath submission -Filter 'sprints-delivery-*.json' |
    Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
if (-not $deliveryReceipt) { throw 'Build and validate a versioned delivery first.' }
$delivery = Get-Content -LiteralPath $deliveryReceipt.FullName -Raw | ConvertFrom-Json
Set-Location -LiteralPath $delivery.publish_folder
git init -b main
git add --dry-run .
git status --short
# Inspect the exact file list and the security/size findings before staging.
git add .
git diff --cached --stat
git diff --cached --check
git commit -m 'Prepare Sprints offline graduation project'
```

No commit identity is configured automatically. If Git requests one, use the identity you intend to associate with this project.

## Remote commands requiring separate approval

After explicit authorization, create an empty **private** GitHub repository using your account. Then replace the placeholder below with its real URL. These commands are prepared and have not been executed:

```powershell
git remote add origin https://github.com/YOUR_ACCOUNT/sprints-ai-orchestrator.git
git remote -v
git push -u origin main
```

Record the actual repository URL and commit hash in a new delivery note, then build a new versioned ZIP. Do not edit a prior manifest or claim a placeholder is a shareable URL. Do not run the legacy `scripts/package_submission.py`; it writes fixed output names. Use `scripts/finalize_delivery.py` for a new versioned package.
