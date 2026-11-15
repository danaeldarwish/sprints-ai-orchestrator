"""Additional authorization, provider fail-closed and exact-token regressions."""
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage,HumanMessage
from langgraph.types import Command
from pydantic import ValidationError
from src.auth import AuthorizationError,require_learner
from src.service import OrchestratorService
from src.heuristics import HeuristicReasoner
from src.tools import db_queries as db,rag_retriever as rag
from src.tokens import _encoder

def test_exact_overlap_offsets_and_reencoded_token_sequences():
    text=" ".join(f"Sentence number {i} explains alpha beta gamma delta." for i in range(400))
    chunks=rag.chunk_documents([Document(page_content=text,metadata={"source":"test"})])
    enc=_encoder();raw=enc.encode(text)
    for index,chunk in enumerate(chunks):
        meta=chunk.metadata
        assert enc.encode(chunk.page_content)==raw[meta["token_start"]:meta["token_end"]]
        assert len(enc.encode(chunk.page_content))<=500
        if index:
            prev=chunks[index-1].metadata
            assert prev["token_end"]-meta["token_start"]==50
            assert enc.encode(chunks[index-1].page_content)[-50:]==enc.encode(chunk.page_content)[:50]

def test_parallel_tool_contexts_do_not_cross(identity):
    def lookup(n):
        token=identity.issue_mock_session(f"learner-{n}")
        with identity.bind(token):
            own=json.loads(db.get_learner_profile.invoke({"learner_id":f"SPR-{n}"}))
            other=json.loads(db.get_learner_profile.invoke({"learner_id":f"SPR-{1002 if n==1001 else 1001}"}))
            return own["learner_id"],other["status"]
    with ThreadPoolExecutor(2) as pool: out=list(pool.map(lookup,[1001,1002]))
    assert out==[("SPR-1001","unable_to_verify"),("SPR-1002","unable_to_verify")]

def test_review_does_not_accept_another_pending_id(app,identity):
    a=identity.issue_mock_session("learner-1013");b=identity.issue_mock_session("learner-1018")
    reviewer=identity.issue_mock_session("career-reviewer")
    pa=app.ask(a,{"text":"openings"});pb=app.ask(b,{"text":"openings"})
    with pytest.raises(ValidationError):
        app.review(reviewer,{"pending_id":pa["pending_id"],"approved":True,"note":"forged","learner_id":"SPR-1018"})
    app.review(reviewer,{"pending_id":pb["pending_id"],"approved":False,"note":"explicit fixture rejection"})
    assert app.snapshot(a)["status"]=="pending_human_review"
    assert app.snapshot(b)["status"]=="rejected_by_human"

@pytest.mark.parametrize("method",["classify_intent","assess_context","reformulate","compose_answer"])
def test_reasoner_failure_degrades_without_fabricated_answer(identity,method):
    class Broken(HeuristicReasoner):pass
    def fail(*args,**kwargs):raise RuntimeError("provider fixture failure")
    setattr(Broken,method,fail)
    app=OrchestratorService(identity,reasoner=Broken(),warm=False)
    token=identity.issue_mock_session("learner-1001")
    question="How do I make my agent remember each student?" if method=="reformulate" else "How is a Python assignment scored?"
    out=app.ask(token,{"text":question})
    assert out["status"]=="unable_to_verify" and out["fallback"]["source"]=="reasoner"

def test_live_adapters_block_before_provider_instantiation(monkeypatch):
    import src.llm as llm
    from src import config
    import langchain_openai
    monkeypatch.setattr(config,"LIVE_CALLS_AUTHORIZED",False)
    monkeypatch.setattr(config,"LLM_PROVIDER","openai")
    monkeypatch.setattr(config,"EMBEDDINGS","openai")
    monkeypatch.setattr(langchain_openai,"ChatOpenAI",lambda *a,**k:pytest.fail("provider instantiated before authorization"))
    with pytest.raises(PermissionError):llm.LLMReasoner()
    with pytest.raises(PermissionError):llm.get_react_model()
    with pytest.raises(PermissionError):rag.get_embedding_function()
