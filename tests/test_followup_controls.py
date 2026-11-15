"""Regression tests for measured startup failure and observed Engine JSON schemas."""
import json
from types import SimpleNamespace
import pytest
from src.tools import code_repl as sandbox,rag_retriever as rag
@pytest.mark.parametrize('fields,available',[
    ({'CpuCfsQuota':True},True),({'CPUCfsQuota':True},True),
    ({'CpuCfsQuota':False},False),({},False),
    ({'CpuCfsQuota':True,'CPUCfsQuota':False},False),
    ({'CpuCfsQuota':'true'},False),
])
def test_engine_json_cpu_capability_aliases(monkeypatch,fields,available):
    monkeypatch.setenv('SPRINTS_SANDBOX_IMAGE','sha256:'+'a'*64)
    monkeypatch.setattr(sandbox,'_docker_prefix',lambda cfg:['local-fixture'])
    def control(prefix,args,timeout=8):
        data={'OSType':'linux','MemoryLimit':True,'SwapLimit':True,'PidsLimit':True,'SecurityOptions':['name=seccomp,profile=builtin'],**fields} if args[0]=='info' else {'Os':'linux','Id':'sha256:'+'a'*64}
        return SimpleNamespace(returncode=0,stdout=json.dumps(data))
    monkeypatch.setattr(sandbox,'_control',control)
    assert sandbox.sandbox_capabilities()['available'] is available

def test_unconfined_seccomp_is_not_accepted(monkeypatch):
    monkeypatch.setattr(sandbox,'_docker_prefix',lambda cfg:['local-fixture'])
    monkeypatch.setattr(sandbox,'_control',lambda *a:SimpleNamespace(returncode=0,stdout=json.dumps({'OSType':'linux','MemoryLimit':True,'SwapLimit':True,'PidsLimit':True,'CpuCfsQuota':True,'SecurityOptions':['name=seccomp,profile=unconfined']})))
    assert not sandbox.sandbox_capabilities()['available']

def test_failed_startup_does_not_advertise_readiness(monkeypatch):
    monkeypatch.setattr(rag,'retrieve',lambda *a,**k:(_ for _ in ()).throw(rag.RetrievalTimeout('fixture')))
    with pytest.raises(rag.RetrievalTimeout):rag.warm_up()

def test_empty_index_does_not_advertise_readiness(monkeypatch):
    monkeypatch.setattr(rag,'retrieve',lambda *a,**k:rag.RetrievalResult('warm up',[],1))
    with pytest.raises(RuntimeError,match='no source chunks'):rag.warm_up()


def test_operational_collection_error_does_not_reingest(monkeypatch):
    from types import SimpleNamespace
    rag._collection.cache_clear()
    client=SimpleNamespace(get_collection=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('fixture unavailable')))
    monkeypatch.setattr(rag,'_client',lambda:client)
    monkeypatch.setattr(rag,'ingest_curriculum',lambda:pytest.fail('Operational failure must not rebuild data'))
    try:
        with pytest.raises(RuntimeError,match='unavailable'):rag._collection()
    finally:rag._collection.cache_clear()

def test_only_missing_collection_triggers_preparation(monkeypatch):
    from types import SimpleNamespace
    from chromadb.errors import NotFoundError
    rag._collection.cache_clear();calls=[];found=object()
    def get(*a,**k):
        if not calls:raise NotFoundError('fixture absent')
        return found
    monkeypatch.setattr(rag,'_client',lambda:SimpleNamespace(get_collection=get))
    monkeypatch.setattr(rag,'ingest_curriculum',lambda:calls.append('prepared'))
    try:
        assert rag._collection() is found and calls==['prepared']
    finally:rag._collection.cache_clear()
