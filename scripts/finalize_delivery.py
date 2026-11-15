"""Create a new private Sprints delivery without replacing any prior artifact.

Uses the installed environment to validate a clean source copy. It never invokes
human review, paid providers, Git publication, or screen recording. All receipts
and archives use exclusive creation; supplied databases and evidence are read-only.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TREES = ("src", "tests", "scripts", "docs", "data", "notebooks", "sandbox", "_client_sources", "evidence")
ROOT_FILES = ("README.md", ".gitignore", ".env.example", "pytest.ini", "requirements.txt", "requirements-lock.txt", "requirements-artifacts.txt", "FINAL_DELIVERY_NOTE.md")
SKIP = {"__pycache__", ".pytest_cache", ".ipynb_checkpoints", "node_modules", ".git", ".aws", ".codex", ".agents", ".chroma", ".build"}
SECRET_PATTERNS = {
    "provider_key": re.compile(rb"sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}"),
    "github_token": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})"),
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "aws_access_id": re.compile(rb"(?:AKIA|ASIA)[A-Z0-9]{16}"),
    "credential_url": re.compile(rb"https?://[^\s/@:]+:[^\s/@]+@"),
}


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_new(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("x", encoding="utf-8", newline="\n") as f:
        f.write(value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=True) + "\n")


def valid_member(name):
    p = PurePosixPath(name)
    if not name or "\\" in name or p.is_absolute() or any(x in ("", ".", "..") for x in name.rstrip("/").split("/")):
        raise ValueError("Unsafe archive path: " + name)
    for part in p.parts:
        if ":" in part or part.rstrip(". ") != part or re.fullmatch(r"(?i)(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", part):
            raise ValueError("Unsafe Windows archive path: " + name)


def forbidden(name):
    parts = PurePosixPath(name).parts
    leaf = parts[-1]
    return any(x in SKIP or x.startswith((".venv", ".chart-data-")) for x in parts) or (
        leaf.startswith(".env") and leaf != ".env.example"
    ) or leaf.lower().endswith((".pyc", ".pyo", ".pem", ".key", ".db-wal", ".db-shm", ".db-journal")) or leaf.lower() in {"credentials.json", "token.json", "id_rsa", "id_ed25519"}


def payload():
    for name in ROOT_FILES:
        p = ROOT / name
        if not p.is_file():
            raise ValueError("Missing root file: " + name)
        yield p, name
    for tree in TREES:
        for current, dirs, files in os.walk(ROOT / tree, followlinks=False):
            dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith((".venv", ".chart-data-"))]
            for d in dirs:
                if (Path(current) / d).is_symlink() or (hasattr(Path, "is_junction") and (Path(current) / d).is_junction()):
                    raise ValueError("Linked directory is not publishable")
            for name in files:
                p = Path(current) / name
                rel = p.relative_to(ROOT).as_posix()
                if forbidden(rel):
                    continue
                if p.is_symlink():
                    raise ValueError("Linked file is not publishable: " + rel)
                yield p, rel
    for p in sorted((ROOT / "submission").iterdir()):
        if p.suffix in {".pdf", ".pptx"} or p.name == "audit_manifest.json":
            yield p, p.relative_to(ROOT).as_posix()


def scan_files(base):
    findings = []
    scanned = {"files": 0, "nested_archives": 0, "expanded_bytes": 0}

    def scan(data, label, depth=0):
        scanned["files"] += 1
        scanned["expanded_bytes"] += len(data)
        if scanned["files"] > 20000 or scanned["expanded_bytes"] > 200_000_000:
            raise ValueError("Security scan expansion limit exceeded")
        for kind, pattern in SECRET_PATTERNS.items():
            if pattern.search(data):
                findings.append({"path": label, "kind": kind})
        if data.startswith(b"PK\x03\x04"):
            if depth >= 4:
                raise ValueError("Nested archive scan depth exceeded")
            scanned["nested_archives"] += 1
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if z.testzip() is not None:
                    raise ValueError("Nested archive CRC failure: " + label)
                seen = set()
                for member in z.infolist():
                    valid_member(member.filename)
                    lowered = member.filename.casefold()
                    if lowered in seen or member.flag_bits & 1:
                        raise ValueError("Duplicate/encrypted nested entry: " + label)
                    seen.add(lowered)
                    if member.is_dir():
                        continue
                    if member.file_size > 50_000_000:
                        raise ValueError("Oversized nested member: " + label)
                    if forbidden(member.filename):
                        findings.append({"path": label + "!" + member.filename, "kind": "forbidden_nested_path"})
                    scan(z.read(member), label + "!" + member.filename, depth + 1)

    for p in sorted(base.rglob("*")):
        if p.is_file():
            rel = p.relative_to(base).as_posix()
            if forbidden(rel):
                findings.append({"path": rel, "kind": "forbidden_path"})
            scan(p.read_bytes(), rel)
    return {"scope": "All payload bytes, recursively expanded ZIP/PPTX/XLSX members; PDF extracted text/metadata and read-only SQLite text inspected separately", "patterns": list(SECRET_PATTERNS), "findings": findings, **scanned,
            "limitations": ["Pattern scan is not a guarantee of absence of all secrets", "Supplied learner names, progress and salary preferences are intentionally included; keep private and obtain publication authorization"]}


def junit(p):
    cases = ET.parse(p).getroot().findall(".//testcase")
    failed = sum(c.find("failure") is not None or c.find("error") is not None for c in cases)
    skipped = sum(c.find("skipped") is not None for c in cases)
    return {"total": len(cases), "passed": len(cases) - failed - skipped, "failed": failed, "skipped": skipped}


def static_checks(base):
    from pypdf import PdfReader
    broken, syntax_count, formats = [], 0, {}
    for folder in ("src", "tests", "scripts"):
        for p in (base / folder).rglob("*.py"):
            ast.parse(p.read_text(encoding="utf-8-sig"), filename=str(p))
            syntax_count += 1
    for p in [base / "README.md", base / "FINAL_DELIVERY_NOTE.md", *(base / "docs").rglob("*.md"), *(base / "_client_sources").glob("*.md")]:
        text = p.read_text(encoding="utf-8-sig")
        for href in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = href.strip("<>").split("#", 1)[0]
            if target and not (p.parent / target).exists():
                broken.append({"file": p.relative_to(base).as_posix(), "target": target})
    for n in ("technical_report_current.pdf", "stakeholder_presentation_current.pdf"):
        reader = PdfReader(base / "submission" / n)
        text = "\n".join(p.extract_text() or "" for p in reader.pages) + str(reader.metadata)
        formats[n] = {"pages": len(reader.pages), "text_extractable": bool(text.strip())}
        if any(pat.search(text.encode()) for pat in SECRET_PATTERNS.values()):
            raise ValueError("Potential secret in extracted PDF text/metadata")
    with zipfile.ZipFile(base / "submission/stakeholder_presentation_current.pptx") as z:
        formats["pptx_slides"] = sum(bool(re.fullmatch(r"ppt/slides/slide\d+\.xml", n)) for n in z.namelist())
        if any(n.startswith("ppt/vbaProject") or n.startswith("ppt/activeX/") for n in z.namelist()):
            raise ValueError("Unexpected active presentation content")
    notebooks = {}
    for p in (base / "notebooks").glob("*.ipynb"):
        n = json.loads(p.read_text(encoding="utf-8-sig"))
        cells = [c for c in n["cells"] if c["cell_type"] == "code"]
        notebooks[p.name] = {"code_cells": len(cells), "executed_cells": sum(c.get("execution_count") is not None for c in cells), "errors": sum(o.get("output_type") == "error" for c in cells for o in c.get("outputs", []))}
    conn = sqlite3.connect((base / "data/sprints_learner.db").resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    db = {"integrity": conn.execute("PRAGMA integrity_check").fetchone()[0]}
    for table in ("learners", "partner_openings"):
        rows = conn.execute('SELECT * FROM "' + table + '"').fetchall()
        db[table] = len(rows)
        if any(p.search(str(rows).encode()) for p in SECRET_PATTERNS.values()):
            raise ValueError("Potential credential in supplied SQLite text")
    conn.close()
    result = {"python_files_parsed": syntax_count, "broken_current_markdown_links": broken, "artifacts": formats, "notebooks": notebooks, "sqlite": db,
              "full_suite_preserved": junit(base / "evidence/followup_20261115/verified_pid/full_tests.xml"),
              "focused_suite_preserved": junit(base / "evidence/demonstration_20261115/targeted_tests_final.xml")}
    assert not broken, broken
    assert db == {"integrity": "ok", "learners": 25, "partner_openings": 16}, db
    assert formats["technical_report_current.pdf"]["pages"] == 16
    assert formats["stakeholder_presentation_current.pdf"]["pages"] == formats["pptx_slides"] == 10
    assert notebooks["evaluator_optimizer_verified.ipynb"] == {"code_cells": 4, "executed_cells": 4, "errors": 0}
    assert result["full_suite_preserved"]["passed"] == 157 and result["focused_suite_preserved"]["passed"] == 70
    return result


def clean_env(runtime):
    names = ("SystemRoot", "WINDIR", "PATH", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA", "APPDATA", "COMSPEC", "PATHEXT", "NUMBER_OF_PROCESSORS")
    env = {n: os.environ[n] for n in names if n in os.environ}
    image = json.loads((ROOT / "evidence/followup_20261115/sandbox_image.json").read_text())["image"]["id"]
    env.update(PYTHONIOENCODING="utf-8", PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", SPRINTS_LLM="offline", SPRINTS_EMBEDDINGS="hashing", SPRINTS_LIVE_AUTHORIZED="0", ANONYMIZED_TELEMETRY="False", LANGSMITH_TRACING="false", LANGCHAIN_TRACING_V2="false", SPRINTS_SANDBOX_IMAGE=image, SPRINTS_DB_PATH=str(runtime / "learners.db"), SPRINTS_CHROMA_DIR=str(runtime / "chroma"))
    return env


def execute(name, command, cwd, env, out):
    began = time.perf_counter()
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    receipt = {"at": datetime.now(timezone.utc).isoformat(), "command": command, "cwd": str(cwd), "exit_code": result.returncode, "duration_s": round(time.perf_counter() - began, 3), "mode": "offline/hashing; credential-free child environment"}
    write_new(out / (name + ".stdout.txt"), result.stdout)
    write_new(out / (name + ".stderr.txt"), result.stderr)
    write_new(out / (name + ".json"), receipt)
    print(json.dumps({"step": name, "exit_code": result.returncode}), flush=True)
    if result.returncode:
        raise RuntimeError(name + " failed; inspect its preserved new receipt")
    return receipt, result.stdout


def scenes(text):
    result = {}
    for chunk in text.split("SCENARIO ")[1:]:
        name, _, body = chunk.partition("\n")
        for match in re.finditer(r"\{", body):
            try:
                value, _ = json.JSONDecoder().raw_decode(body[match.start():])
                if isinstance(value, dict) and "status" in value:
                    result[name.strip()] = value
                    break
            except ValueError:
                pass
    assert result["curriculum"]["sources"]
    assert result["buggy_code"]["assessment"]["score"] == 60
    assert result["buggy_code"]["assessment"]["pass_status"] == "fail"
    assert result["corrected_code"]["assessment"]["score"] == 100
    assert result["corrected_code"]["assessment"]["pass_status"] == "pass"
    assert result["database_career"]["status"] == "released" and "EGP" in result["database_career"]["final_answer"]
    assert result["tier1_pending"]["status"] == "pending_human_review"
    assert not result["other_learner_denied"].get("assessment")
    assert result["other_learner_denied"]["status"] == "denied"
    assert result["other_learner_denied"]["route"] == "deny"
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--audit-dir", type=Path)
    ap.add_argument("--execution-evidence", type=Path, help="Reuse a preserved successful ordinary demo when application/data hashes still match its clean source copy")
    args = ap.parse_args()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    audit = args.audit_dir.resolve() if args.audit_dir else ROOT / "evidence" / ("final_delivery_" + stamp)
    assert audit.is_relative_to((ROOT / "evidence").resolve())
    audit.mkdir(parents=True, exist_ok=True)
    if (audit / "validation.json").exists():
        raise ValueError("Use a fresh audit directory")
    stage = ROOT / ".build" / ("publish-" + stamp)
    stage.mkdir(parents=True, exist_ok=False)
    baseline = {rel: digest(p) for p, rel in payload()}
    for p, rel in payload():
        dest = stage / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, dest)
    static = static_checks(stage)
    scan = scan_files(stage)
    assert not scan["findings"], scan["findings"]
    write_new(audit / "static_checks.json", static)
    write_new(audit / "security_scan.json", scan)
    runtime = ROOT / ".build" / ("validation-runtime-" + stamp)
    runtime.mkdir()
    env = clean_env(runtime)
    commands = []
    for name, cmd in (("dependency_check", [sys.executable, "-m", "pip", "check"]), ("build_demo_db", [sys.executable, "-m", "src.main", "build-db"]), ("ingest", [sys.executable, "-m", "src.main", "ingest"]), ("readiness", [sys.executable, "-m", "src.main", "readiness"]), ("sandbox_status", [sys.executable, "-m", "src.main", "sandbox-status"]), ("offline_demo", [sys.executable, "-m", "src.main", "demo", "--verbose"])):
        if args.execution_evidence:
            previous = args.execution_evidence.resolve()
            assert previous.is_relative_to((ROOT / "evidence").resolve())
            receipt = json.loads((previous / (name + ".json")).read_text())
            assert receipt["exit_code"] == 0
            old_stage = Path(receipt["cwd"]).resolve()
            assert old_stage.is_relative_to((ROOT / ".build").resolve())
            # Source equality, not an exit code alone, justifies reusing this run.
            for folder in ("src", "data", "sandbox"):
                for current_file in (stage / folder).rglob("*"):
                    if current_file.is_file():
                        assert digest(current_file) == digest(old_stage / current_file.relative_to(stage))
            assert digest(stage / "requirements-lock.txt") == digest(old_stage / "requirements-lock.txt")
            for suffix in ("json", "stdout.txt", "stderr.txt"):
                source = previous / (name + "." + suffix)
                write_new(audit / source.name, source.read_text(encoding="utf-8"))
            stdout = (previous / (name + ".stdout.txt")).read_text(encoding="utf-8")
            print(json.dumps({"step": name, "preserved_exit_code": 0, "reused_from": str(previous)}), flush=True)
        else:
            receipt, stdout = execute(name, cmd, stage, env, audit)
        commands.append(receipt)
        if name == "readiness":
            ready = json.loads(stdout)
            assert ready["status"] == "READY" and ready["accepting_learner_requests"]
        elif name == "sandbox_status":
            assert json.loads(stdout)["available"], "Sandbox unavailable; no actual demo grade claim"
        elif name == "offline_demo":
            demo = scenes(stdout)
    preserved = {}
    for record_file in ("prior_submission_hashes.json", "prior_evidence_hashes.json"):
        p = audit / record_file
        if p.exists():
            records = json.loads(p.read_text())
            mismatches = [x["path"] for x in records if digest(ROOT / x["path"]) != x["sha256"]]
            preserved[record_file] = {"checked_files": len(records), "mismatches": mismatches}
            assert not mismatches, mismatches
    assert all(digest(ROOT / n) == h for n, h in baseline.items()), "Source changed during validation"
    local = {"at": datetime.now(timezone.utc).isoformat(), "static": static, "security": scan, "commands": commands, "execution_reused_from": str(args.execution_evidence.resolve()) if args.execution_evidence else None, "execution_reuse_basis": "Application/data/sandbox/lock bytes match the source copy named in the original execution receipts" if args.execution_evidence else None, "actual_demo_checks_pass": True, "demo_scenarios": {n: {k: v for k, v in d.items() if k in ("status", "route", "assessment", "refinement_count", "sources")} for n, d in demo.items()}, "prior_artifacts_preserved": preserved, "application_source_changed": False, "full_suite_repeated": False, "fresh_environment_installation_repeated": False, "paid_requests": 0, "automated_human_decisions": 0, "video": "PENDING", "github_url": None, "verdict": "NOT READY"}
    write_new(audit / "validation.json", local)
    # Refresh only this new evidence directory in the clean copy after validation.
    staged_audit = stage / audit.relative_to(ROOT)
    shutil.copytree(audit, staged_audit, dirs_exist_ok=True)
    files = {p.relative_to(stage).as_posix(): {"sha256": digest(p), "bytes": p.stat().st_size} for p in sorted(stage.rglob("*")) if p.is_file()}
    manifest = {"schema": "sprints-final-delivery-v1", "created_utc": datetime.now(timezone.utc).isoformat(), "verdict": "NOT READY", "delivery_note": "FINAL_DELIVERY_NOTE.md", "video": "PENDING", "github_url": None, "live_inference": "NOT EXECUTED", "cold_retrieval": "PARTIAL", "full_suite_preserved": static["full_suite_preserved"], "focused_suite_preserved": static["focused_suite_preserved"], "demo": "Actual current source, Linux container, Chroma, SQLite and graph; deterministic offline reasoning", "human_review": "User reports interactive APPROVE/REJECT PASS; independently preserved API evidence is labeled automated fixtures; no new human interaction performed", "files": files, "manifest_hash_rule": "This manifest excludes its own hash; archive SHA256 and post-extraction results are external"}
    write_new(stage / "PACKAGE_MANIFEST.json", manifest)
    archive = ROOT / "submission" / ("sprints-ai-orchestrator-SUBMISSION-" + stamp + ".zip")
    with zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(stage.rglob("*")):
            if p.is_file():
                z.write(p, "sprints-ai-orchestrator/" + p.relative_to(stage).as_posix())
    extraction = ROOT / ".build" / ("extracted-" + stamp)
    extraction.mkdir()
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        seen = set()
        for info in z.infolist():
            valid_member(info.filename)
            assert info.filename.casefold() not in seen
            seen.add(info.filename.casefold())
            assert (extraction / info.filename).resolve().is_relative_to(extraction.resolve())
            assert not (info.external_attr >> 16) & 0o170000 == 0o120000
        z.extractall(extraction)
    extracted = extraction / "sprints-ai-orchestrator"
    for n, item in files.items():
        assert digest(extracted / n) == item["sha256"], n
    assert digest(extracted / "PACKAGE_MANIFEST.json") == digest(stage / "PACKAGE_MANIFEST.json")
    assert len([p for p in extracted.rglob("*") if p.is_file()]) == len(files) + 1
    extracted_scan = scan_files(extracted)
    assert not extracted_scan["findings"]
    static_checks(extracted)
    receipt, _ = execute("extracted_import", [sys.executable, "-c", "from pathlib import Path; import src,src.agents.orchestrator,src.service; assert Path(src.__file__).resolve().is_relative_to(Path.cwd()); print(Path(src.__file__).resolve())"], extracted, env, audit)
    total = sum(x["bytes"] for x in files.values())
    largest = sorted(({"path": p, **v} for p, v in files.items()), key=lambda x: x["bytes"], reverse=True)[:10]
    final = {"archive": str(archive), "sha256": digest(archive), "archive_bytes": archive.stat().st_size, "payload_files": len(files), "payload_bytes": total, "largest_files": largest, "files_over_10MiB": [x for x in largest if x["bytes"] > 10 * 1024 * 1024], "crc": "PASS", "safe_extraction": "PASS", "payload_hashes": "ALL MATCH", "extracted_security_scan": extracted_scan, "extracted_import": receipt, "publish_folder": str(stage), "extracted_folder": str(extracted), "validation_evidence": str(audit), "video": "PENDING", "github_url": None, "live_inference": "NOT EXECUTED", "cold_retrieval": "PARTIAL", "verdict": "NOT READY", "missing": ["Genuine reviewed 180-300 second recording", "Authorized GitHub publication and actual repository URL"], "technical_gaps": ["Live language reasoning and LLM-as-Judge unexecuted", "Cold retrieval criterion partial", "Production identity and durable state absent", "Original kickoff media unavailable; 80% waiting target unmeasured"]}
    write_new(archive.with_suffix(".zip.sha256"), final["sha256"] + "  " + archive.name + "\n")
    write_new(ROOT / "submission" / ("sprints-delivery-" + stamp + ".json"), final)
    write_new(audit / "archive_validation.json", final)
    print(json.dumps(final, indent=2), flush=True)


if __name__ == "__main__":
    main()
