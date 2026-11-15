"""Fresh-process unprepared/prepared RAG benchmark; retains every slow sample."""
from pathlib import Path
import sys,os,time,json,subprocess,tempfile,hashlib,platform
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OUT=ROOT/'evidence'/'followup_20261115'
QUERIES=['python rubric','chroma chunk overlap','langgraph state','interrupt approval','memory thread id']
QUALITY=[('How is a Python assignment scored?','01_'),('what chunk size and overlap does ingestion use','03_'),('how do I pause the graph for a human reviewer interrupt','05_'),('which partner is tier-1 and needs approval','06_'),('what is a ReAct agent tool message','02_')]
def checked_result(rag,q):
    t=time.perf_counter();r=rag.retrieve(q,timeout_ms=30000);elapsed=(time.perf_counter()-t)*1000
    assert r.chunks
    for c in r.chunks:
        assert c['text'] in (rag.config.CURRICULUM_DIR/c['source']).read_text(encoding='utf-8')
    return {'query':q,'latency_ms':elapsed,'sources':[[c['source'],c['chunk_index']] for c in r.chunks]}
def worker(mode,index):
    t=time.perf_counter();from src.tools import rag_retriever as rag
    imports=(time.perf_counter()-t)*1000
    if mode=='--prepared':
        startup=rag.warm_up();r=checked_result(rag,QUERIES[index%5]);print(json.dumps({'import_ms':imports,'readiness_ms':startup,**r}))
    elif mode=='--cold':print(json.dumps({'import_ms':imports,**checked_result(rag,QUERIES[index%5])}))
    else:
        startup=rag.warm_up();quality=[]
        for q,expected in QUALITY:
            r=checked_result(rag,q);assert r['sources'][0][0].startswith(expected);quality.append(r)
        samples=[checked_result(rag,q) for q in QUERIES*40]
        print(json.dumps({'readiness_ms':startup,'quality':quality,'samples':samples}))
def main():
    from scripts.record_command import safe_env
    from scripts.benchmark_rag import summary
    with tempfile.TemporaryDirectory(prefix='sprints-ready-bench-') as tmp:
        env=safe_env();env['SPRINTS_CHROMA_DIR']=str(Path(tmp)/'chroma')
        def child(mode,*args):
            t=time.perf_counter();p=subprocess.run([sys.executable,'scripts/benchmark_rag.py','--ingest'] if mode=='--ingest' else [sys.executable,str(Path(__file__).resolve()),mode,*map(str,args)],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
            if p.returncode:raise RuntimeError(p.stderr)
            return json.loads(p.stdout.strip().splitlines()[-1]),(time.perf_counter()-t)*1000
        proof,_=child('--ingest');cold=[];prepared=[]
        for i in range(20):
            r,d=child('--cold',i);cold.append({**r,'process_ms':d})
            r,d=child('--prepared',i);prepared.append({**r,'process_ms':d})
            print('Completed fresh-process pair',i+1,flush=True)
        warm,_=child('--warm')
    result={'backend':'Actual ChromaDB PersistentClient; local 1024-dimensional hashing embeddings','method':'Nearest-rank; 20 alternating fresh-process pairs on same persisted corpus; OS caches not flushed; no outliers excluded; 30 s observation window prevents censoring over-1000 ms queries; warm 200 queries; all include embedding/executor dispatch/source attribution checks. Desktop load not controlled. Readiness is additional startup work, not removed cold cost.','platform':platform.platform(),'source_sha256':hashlib.sha256((ROOT/'src/tools/rag_retriever.py').read_bytes()).hexdigest(),'proof':proof,'cold_process':summary([x['process_ms'] for x in cold]),'cold_first_retrieve':summary([x['latency_ms'] for x in cold]),'startup_readiness':summary([x['readiness_ms'] for x in prepared]),'first_after_readiness':summary([x['latency_ms'] for x in prepared]),'warm':summary([x['latency_ms'] for x in warm['samples']]),'cold_samples':cold,'prepared_samples':prepared,'warm_samples':warm['samples'],'quality':warm['quality']}
    (OUT/'rag_latency.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k in ['cold_process','cold_first_retrieve','startup_readiness','first_after_readiness','warm']},indent=2))
if __name__=='__main__': worker(sys.argv[1],int(sys.argv[2]) if len(sys.argv)>2 else 0) if len(sys.argv)>1 else main()
