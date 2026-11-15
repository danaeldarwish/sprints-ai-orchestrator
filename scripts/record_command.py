"""Capture exact local command outputs and real exit codes without credentials."""
from pathlib import Path
from datetime import datetime,timezone
import json,os,subprocess,sys,time
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
sys.stderr.reconfigure(encoding="utf-8",errors="replace")
ROOT=Path(__file__).resolve().parents[1]
def safe_env():
    names=("SystemRoot","WINDIR","PATH","TEMP","TMP","USERPROFILE","LOCALAPPDATA","APPDATA","COMSPEC","PATHEXT","NUMBER_OF_PROCESSORS")
    env={n:os.environ[n] for n in names if n in os.environ}
    env.update(PYTHONIOENCODING="utf-8",PYTHONUTF8="1",SPRINTS_LLM="offline",SPRINTS_EMBEDDINGS="hashing",SPRINTS_LIVE_AUTHORIZED="0",
               ANONYMIZED_TELEMETRY="False",LANGSMITH_TRACING="false",LANGCHAIN_TRACING_V2="false",MPLBACKEND="Agg")
    # Only a nonsecret immutable image ID is accepted by the sandbox.
    if "SPRINTS_SANDBOX_IMAGE" in os.environ: env["SPRINTS_SANDBOX_IMAGE"]=os.environ["SPRINTS_SANDBOX_IMAGE"]
    return env
def record(name,command,timeout=300):
    out=ROOT/"evidence"/"commands"; out.mkdir(parents=True,exist_ok=True)
    start=time.perf_counter()
    timed_out=False
    try:
        result=subprocess.run(command,cwd=ROOT,env=safe_env(),capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=timeout)
        code=result.returncode; stdout=result.stdout; stderr=result.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out=True; code=124
        stdout=(exc.stdout or b"").decode("utf-8","replace") if isinstance(exc.stdout,bytes) else exc.stdout or ""
        stderr="Command timed out. "+str(exc)
    (out/(name+".stdout.txt")).write_text(stdout,encoding="utf-8")
    (out/(name+".stderr.txt")).write_text(stderr,encoding="utf-8")
    meta={"command":command,"cwd":".","at":datetime.now(timezone.utc).isoformat(),"exit_code":code,"timed_out":timed_out,"duration_s":round(time.perf_counter()-start,3)}
    (out/(name+".json")).write_text(json.dumps(meta,indent=2),encoding="utf-8")
    print(json.dumps(meta)); print(stdout[-6000:]); print(stderr[-2000:])
    return code
if __name__=="__main__":
    name=sys.argv[1]; command=sys.argv[2:]
    if command and command[0]=="--": command=command[1:]
    if command and command[0]=="PYTHON": command[0]=sys.executable
    raise SystemExit(record(name,command))
