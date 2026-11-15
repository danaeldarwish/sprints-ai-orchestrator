"""Bounded pre-change cold-path profile, actual Chroma and original query API."""
from pathlib import Path
import subprocess,sys,time,json,tempfile,math,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OUT=ROOT/'evidence'/'followup_20261115'
def worker():
    start=time.perf_counter()
    from src.tools import rag_retriever as rag
    imported=(time.perf_counter()-start)*1000
    stages={}
    orig_client=rag._client;orig_collection=rag._collection
    def client():
        t=time.perf_counter();x=orig_client();stages['client_ms']=(time.perf_counter()-t)*1000;return x
    def collection():
        t=time.perf_counter();x=orig_collection();stages['collection_ms']=(time.perf_counter()-t)*1000;return x
    rag._client=client;rag._collection=collection
    t=time.perf_counter();result=rag.retrieve('how do I pause the graph for a human reviewer interrupt',timeout_ms=30000);elapsed=(time.perf_counter()-t)*1000
    print(json.dumps({'import_ms':imported,'first_retrieve_ms':elapsed,**stages,'query_and_dispatch_ms':elapsed-stages.get('collection_ms',0),'top_source':result.chunks[0]['source']}))
def main():
    from scripts.record_command import safe_env
    from scripts.benchmark_rag import summary
    with tempfile.TemporaryDirectory(prefix='sprints-profile-') as tmp:
        env=safe_env();env['SPRINTS_CHROMA_DIR']=str(Path(tmp)/'chroma')
        p=subprocess.run([sys.executable,'scripts/benchmark_rag.py','--ingest'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
        if p.returncode:raise RuntimeError(p.stderr)
        samples=[]
        for i in range(5):
            t=time.perf_counter();p=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--worker'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=60)
            if p.returncode:raise RuntimeError(p.stderr)
            samples.append({**json.loads(p.stdout.strip().splitlines()[-1]),'process_ms':(time.perf_counter()-t)*1000})
    result={'source_sha256':hashlib.sha256((ROOT/'src/tools/rag_retriever.py').read_bytes()).hexdigest(),'n':len(samples),'method':'Fresh Python processes, same persisted eight-chunk corpus, OS cache not flushed; instrumentation included; all samples retained','samples':samples,'summary':{k:summary([s[k] for s in samples]) for k in samples[0] if k.endswith('_ms')}}
    (OUT/'rag_profile_before.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':worker() if '--worker' in sys.argv else main()
