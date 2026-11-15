"""Package only this project and independently test a fresh extraction."""
from pathlib import Path,PurePosixPath
import os,sys,json,zipfile,hashlib,subprocess,uuid,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.record_command import safe_env
EXCLUDE={".git",".venv",".venv-audit",".build",".chroma",".pytest_cache","__pycache__",".ipynb_checkpoints"}
def payload():
    for current,dirs,names in os.walk(ROOT):
        dirs[:]=[d for d in dirs if d not in EXCLUDE and not d.startswith(".venv")]
        for n in names:
            p=Path(current)/n;rel=p.relative_to(ROOT).as_posix()
            if n.endswith((".pyc",".pyo")) or n==".env":continue
            if rel.startswith("submission/") and p.suffix not in {".pdf",".pptx"}:continue
            if rel.startswith("evidence/archive") or "launcher" in n:continue
            yield p,rel
def package():
    out=ROOT/"submission";out.mkdir(exist_ok=True)
    archive=out/"sprints-ai-orchestrator-final.zip"
    files=sorted(payload(),key=lambda x:x[1]);manifest={rel:hashlib.sha256(p.read_bytes()).hexdigest() for p,rel in files}
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p,rel in files:z.write(p,"sprints-ai-orchestrator/"+rel)
        z.writestr("sprints-ai-orchestrator/PACKAGE_MANIFEST.json",json.dumps({"schema":"sprints-payload-v1","files":manifest},indent=2))
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    (out/"sprints-ai-orchestrator-final.zip.sha256").write_text(digest+"  "+archive.name+"\n",encoding="ascii")
    return archive,manifest,digest
def verify(archive,manifest,digest):
    base=ROOT/".build"/("archive-"+uuid.uuid4().hex);base.mkdir()
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for entry in z.infolist():
            p=(base/entry.filename).resolve()
            if not p.is_relative_to(base.resolve()):raise ValueError("Unsafe ZIP path")
            if any(part in EXCLUDE for part in PurePosixPath(entry.filename).parts):raise ValueError("Excluded file present")
        z.extractall(base)
    extracted=base/"sprints-ai-orchestrator"
    for name,expected in manifest.items():
        assert hashlib.sha256((extracted/name).read_bytes()).hexdigest()==expected,name
    commands=[
      ("archive_import",[sys.executable,"-c","from pathlib import Path; import src; import src.agents.orchestrator; print(Path(src.__file__).resolve()); assert Path(src.__file__).resolve().is_relative_to(Path.cwd())"]),
      ("archive_tests",[sys.executable,"-m","pytest","--junitxml="+str(ROOT/"evidence/archive_tests.xml"),"-rs"]),
      ("archive_demo",[sys.executable,"-m","src.main","demo","--verbose"]),
    ];results=[]
    for name,cmd in commands:
        t=time.perf_counter();p=subprocess.run(cmd,cwd=extracted,env=safe_env(),capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=180)
        (ROOT/"evidence"/(name+".stdout.txt")).write_text(p.stdout,encoding="utf-8")
        (ROOT/"evidence"/(name+".stderr.txt")).write_text(p.stderr,encoding="utf-8")
        result={"name":name,"command":cmd,"exit_code":p.returncode,"duration_s":round(time.perf_counter()-t,3)}
        results.append(result);print(json.dumps(result));print(p.stdout[-2000:]);print(p.stderr[-500:])
        if p.returncode:raise RuntimeError(name+" failed")
    result={"archive":str(archive),"sha256":digest,"zip_integrity":"PASS","payload_files":len(manifest),
            "all_payload_hashes_match":True,"extraction":str(extracted),"isolated_environment":"fresh .venv-audit installed for this audit; locked versions",
            "commands":results,"live_llm":"NOT VERIFIED","sandbox":"Unable to verify; real integration skipped","video":"PENDING","verdict":"NOT READY"}
    (ROOT/"evidence/archive_verification.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    audit={"schema":"sprints-submission-audit-v1","archive":str(archive),"sha256":digest,"files":manifest,
           "evidence":"../evidence/archive_verification.json","verdict":"NOT READY","missing":["genuine demo video","verified isolated execution","live OpenAI inference after explicit authorization"],"estimated_rubric_score":64,"official_grade":False}
    (ROOT/"submission/audit_manifest.json").write_text(json.dumps(audit,indent=2),encoding="utf-8")
    print(json.dumps({"archive":str(archive),"sha256":digest,"files":len(manifest),"verdict":"NOT READY"}))
if __name__=="__main__":
    archive,manifest,digest=package();verify(archive,manifest,digest)
