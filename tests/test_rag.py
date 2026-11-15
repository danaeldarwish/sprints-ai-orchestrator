"""Sprint 1: ingestion, chunking, retrieval quality and the 1000 ms budget."""
import statistics
import time

import pytest
from langchain_core.documents import Document

from src import config
from src.tools import rag_retriever as rag
from src.tokens import count_tokens


def test_ingestion_report_and_chunk_limits():
    rep = rag.ingest_curriculum()
    assert rep.documents == 6 and rep.chunks >= 6
    assert rep.max_chunk_tokens <= config.CHUNK_TOKENS
    assert (rep.chunk_tokens, rep.chunk_overlap) == (500, 50)


def test_chunker_respects_500_tokens_and_50_token_overlap_on_long_text():
    text = " ".join(f"Sentence number {i} explains alpha beta gamma delta." for i in range(400))
    chunks = rag.chunk_documents([Document(page_content=text, metadata={"source": "long.md"})])
    assert len(chunks) > 3
    assert all(count_tokens(c.page_content) <= 500 for c in chunks)
    # overlap: the start of each chunk is repeated at the end of the previous one
    for prev, nxt in zip(chunks, chunks[1:]):
        assert nxt.page_content[:25] in prev.page_content


@pytest.mark.parametrize("query,expected", [
    ("How is a Python assignment scored?", "01_"),
    ("what chunk size and overlap does ingestion use", "03_"),
    ("how do I pause the graph for a human reviewer interrupt", "05_"),
    ("which partner is tier-1 and needs approval", "06_"),
    ("what is a ReAct agent tool message", "02_"),
])
def test_retrieval_relevance(query, expected):
    top = rag.retrieve(query).chunks[0]
    assert top["source"].startswith(expected)


def test_retrieval_latency_budget_p95_under_1000ms():
    rag.warm_up()
    qs = ["python rubric", "chroma chunk overlap", "langgraph state", "interrupt approval", "memory thread id"] * 12
    lat = []
    for q in qs:
        t = time.perf_counter()
        rag.retrieve(q)
        lat.append((time.perf_counter() - t) * 1000)
    assert max(lat) < config.RETRIEVAL_TIMEOUT_MS
    assert statistics.quantiles(lat, n=20)[18] < 1000  # p95


def test_retrieval_timeout_raises(monkeypatch):
    monkeypatch.setattr(rag, "_query", lambda q, k: time.sleep(0.5))
    with pytest.raises(rag.RetrievalTimeout):
        rag.retrieve("anything", timeout_ms=50)


def test_search_tool_returns_unable_to_verify_on_failure(monkeypatch):
    monkeypatch.setattr(rag, "retrieve", lambda q: (_ for _ in ()).throw(RuntimeError("chroma down")))
    out = rag.search_curriculum.invoke({"query": "x"})
    assert '"unable_to_verify"' in out and '"chroma"' in out
