"""Actual Chroma retrieval benchmark. Isolated child lifecycles release Windows handles.

Nearest-rank percentiles. Process-cold includes interpreter/import/client time;
cold-first-query excludes imports and includes lazy client/index initialization.
OS caches are not flushed. Warm includes embedding and executor dispatch.
"""
from pathlib import Path
import sys,os,time,json,math,subprocess,tempfile,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
QUERIES=["python rubric","chroma chunk overlap","langgraph state","interrupt approval","memory thread id"]
def summary(values):
    a=sorted(values)
    def p(q):return round(a[max(0,math.ceil(len(a)*q)-1)],3)
    return {"n":len(a),"p50_ms":p(.5),"p95_ms":p(.95),"p99_ms":p(.99),"max_ms":round(max(a),3),"below_1000ms_pct":round(100*sum(v<1000 for v in a)/len(a),2)}
def worker(mode):
    from src.tools import rag_retriever as rag
    if mode=="--ingest":
        from dataclasses import asdict
        from src.tokens import _encoder
        report=rag.ingest_curriculum()
        windows=[{**c.metadata,"recount":len(_encoder().encode(c.page_content,disallowed_special=()))} for c in rag.chunk_documents(rag.load_curriculum_documents())]
        corpus={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(rag.config.CURRICULUM_DIR.glob("*.md"))}
        print(json.dumps({"ingest":asdict(report),"token_windows":windows,"corpus_sha256":corpus}))
    elif mode=="--cold":
        t=time.perf_counter();result=rag.retrieve(QUERIES[int(sys.argv[2])%5],timeout_ms=30000)
        print(json.dumps({"first_retrieve_ms":(time.perf_counter()-t)*1000,"hits":len(result.chunks)}))
    else:
        rag.warm_up();values=[]
        for q in QUERIES*40:
            t=time.perf_counter();rag.retrieve(q,timeout_ms=30000);values.append((time.perf_counter()-t)*1000)
        print(json.dumps(values))
def main():
    from scripts.record_command import safe_env
    output=ROOT/"evidence"/"benchmark";output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sprints-benchmark-") as tmp:
        env=safe_env();env["SPRINTS_CHROMA_DIR"]=str(Path(tmp)/"chroma")
        def child(mode,*args):
            t=time.perf_counter()
            p=subprocess.run([sys.executable,str(Path(__file__).resolve()),mode,*map(str,args)],cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
            if p.returncode:raise RuntimeError(p.stderr)
            return json.loads(p.stdout.strip().splitlines()[-1]),(time.perf_counter()-t)*1000
        proof,_=child("--ingest");cold=[];first=[]
        for i in range(10):
            out,duration=child("--cold",i);cold.append(duration);first.append(out["first_retrieve_ms"])
        warm,_=child("--warm")
        result={"backend":"actual ChromaDB PersistentClient; deterministic hashing embeddings",
                "method":"nearest-rank; process-cold, OS cache not flushed; warm includes executor dispatch and embedding",
                "tokenizer":proof["ingest"]["tokenizer"],**proof,
                "cold_process":summary(cold),"cold_first_retrieve":summary(first),"warm":summary(warm),
                "cold_process_samples_ms":cold,"cold_first_retrieve_samples_ms":first,"warm_samples_ms":warm}
        (output/"rag_latency.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
        print(json.dumps({k:v for k,v in result.items() if not k.endswith("_ms") and k!="token_windows"},indent=2))
    print("Benchmark temporary index cleanup: complete")
if __name__=="__main__":
    if len(sys.argv)>1:worker(sys.argv[1])
    else:main()
