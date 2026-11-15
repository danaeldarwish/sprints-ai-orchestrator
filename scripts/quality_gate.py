"""Offline package quality checks. Readiness is separate from technical checks."""
from pathlib import Path
from importlib.metadata import distributions
import csv,json,re,hashlib,sqlite3,sys,platform,urllib.parse
ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={".venv-audit",".venv",".build",".chroma",".pytest_cache","__pycache__",".ipynb_checkpoints","submission"}
def files():
    import os
    for current,dirs,names in os.walk(ROOT):
        dirs[:]=[n for n in dirs if n not in EXCLUDED and not n.startswith(".venv")]
        for name in names:
            if name.endswith((".pyc",".pyo")) or name==".env":continue
            yield Path(current)/name
def main():
    baseline=json.loads((ROOT/"evidence/baseline/archive_manifest.json").read_text())
    known={x["path"]:x["zip_sha256"] for x in baseline["files"]}
    csv_path=ROOT/"data/sprints_learner_db.csv";db_path=ROOT/"data/sprints_learner.db"
    checks={}
    checks["learner_csv_unchanged"]=hashlib.sha256(csv_path.read_bytes()).hexdigest()==known["data/sprints_learner_db.csv"]
    checks["sqlite_original_bytes_unchanged"]=hashlib.sha256(db_path.read_bytes()).hexdigest()==known["data/sprints_learner.db"]
    checks["learner_rows"]=len(list(csv.DictReader(csv_path.open(encoding="utf-8",newline=""))))
    with sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro",uri=True) as con:
        checks["sqlite_integrity"]=con.execute("PRAGMA integrity_check").fetchone()[0]
        checks["sqlite_learners"]=con.execute("SELECT COUNT(*) FROM learners").fetchone()[0]
        checks["synthetic_openings"]=con.execute("SELECT COUNT(*) FROM partner_openings WHERE is_synthetic=1").fetchone()[0]
    b=json.loads((ROOT/"evidence/benchmark/rag_latency.json").read_text())
    checks["benchmark_corpus_matches"]=all(hashlib.sha256((ROOT/"data/curriculum_docs"/n).read_bytes()).hexdigest()==h for n,h in b["corpus_sha256"].items())
    broken=[];secrets=[];changes=[]
    for file in files():
        rel=file.relative_to(ROOT).as_posix()
        if rel.startswith("evidence/rendered/"):continue
        digest=hashlib.sha256(file.read_bytes()).hexdigest()
        if rel in known and digest!=known[rel]:changes.append({"path":rel,"change":"modified","before_sha256":known[rel],"after_sha256":digest})
        elif rel not in known and not rel.startswith("evidence/"):changes.append({"path":rel,"change":"added","sha256":digest})
        if file.suffix in {".md",".py",".json",".txt",".ipynb",".mjs",".yaml",".yml"} or file.name==".env.example":
            text=file.read_text(encoding="utf-8",errors="replace")
            if re.search(r"sk-[A-Za-z0-9_-]{24,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|AIza[0-9A-Za-z_-]{30,}",text):secrets.append(rel)
            if file.suffix==".md":
                for href in re.findall(r"\[[^\]]*\]\(([^)]+)\)",text):
                    if href.startswith(("https://","http://","mailto:","#")):continue
                    target=urllib.parse.unquote(href.strip("<>").split("#",1)[0])
                    if target and not (file.parent/target).exists():broken.append({"file":rel,"target":target})
    checks["broken_internal_links"]=broken;checks["potential_secret_patterns"]=secrets
    checks["original_archive_unchanged"]=None
    original=Path(baseline["archive"])
    if original.exists():checks["original_archive_unchanged"]=hashlib.sha256(original.read_bytes()).hexdigest()==baseline["sha256"]
    checks["video_status"]="PENDING";checks["verdict"]="NOT READY"
    checks["technical_checks_pass"]=bool(checks["learner_csv_unchanged"] and checks["sqlite_original_bytes_unchanged"] and checks["learner_rows"]==checks["sqlite_learners"]==25 and checks["sqlite_integrity"]=="ok" and checks["synthetic_openings"]==16 and checks["benchmark_corpus_matches"] and not broken and not secrets)
    (ROOT/"evidence/quality_gate.json").write_text(json.dumps(checks,indent=2),encoding="utf-8")
    (ROOT/"evidence/change_manifest.json").write_text(json.dumps({"preserved_baseline":"evidence/baseline/original_source.zip","changes":changes},indent=2),encoding="utf-8")
    environment={"python":sys.version,"platform":platform.platform(),"isolated_prefix":str(Path(sys.prefix)),"base_prefix":str(Path(sys.base_prefix)),
                 "packages":sorted([{"name":d.metadata["Name"],"version":d.version} for d in distributions()],key=lambda d:d["name"].lower()),
                 "paid_calls":0,"provider_credentials_read":False,"identity":"local mock sessions only"}
    (ROOT/"evidence/environment.json").write_text(json.dumps(environment,indent=2),encoding="utf-8")
    print(json.dumps(checks,indent=2))
    if not checks["technical_checks_pass"]:raise SystemExit(1)
if __name__=="__main__":main()
