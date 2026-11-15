"""Curriculum ingestion + retrieval (Sprint 1: Document Ingestion & Vectorization).

Pipeline: load curriculum files -> split into 500-token chunks with a 50-token
overlap (exact cl100k_base token windows) -> embed -> persist in
ChromaDB. Retrieval requests the 1000 ms deadline from the acceptance criteria;
cold and warm performance are separately measured, with cold misses disclosed.

Curriculum mapping: powers the Advisor Agent's answers about Modules 1-5 and
the career policy document.
"""
from __future__ import annotations

import hashlib
import logging
import math
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from langchain_core.documents import Document
from langchain_core.tools import tool

from src import config
from src.schemas import UnableToVerify
from src.textutil import content_terms
from src.tokens import count_tokens, tokenizer_name, _encoder

log = logging.getLogger("sprints.rag")
_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="chroma")


class RetrievalTimeout(RuntimeError):
    """Raised when ChromaDB does not answer inside ``RETRIEVAL_TIMEOUT_MS``."""


# ----------------------------------------------------------------- embeddings
def embed_text(text: str, dim: int = 1024) -> list[float]:
    """Deterministic hashed bag-of-words (+bigram) embedding, L2-normalised.

    Offline stand-in for a hosted embedding model: no network or model download
    is needed, results are reproducible, and it is fast enough for the 1 s
    budget. Set ``SPRINTS_EMBEDDINGS=openai`` for ``text-embedding-3-small``.
    """
    vec = [0.0] * dim
    terms = content_terms(text)
    feats = [(t, 1.0) for t in terms] + [(f"{a}_{b}", 0.5) for a, b in zip(terms, terms[1:])]
    counts: dict[str, float] = {}
    for tok, w in feats:
        counts[tok] = counts.get(tok, 0.0) + w
    for tok, w in counts.items():
        idx = zlib.crc32(tok.encode()) % dim
        sign = 1.0 if hashlib.md5(tok.encode()).digest()[0] % 2 == 0 else -1.0
        vec[idx] += sign * (1.0 + math.log(w) if w > 1 else w)
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class HashingEmbeddingFunction(EmbeddingFunction[Documents]):
    """ChromaDB embedding function wrapping :func:`embed_text`."""

    def __init__(self, dim: int = 1024) -> None:
        self.dim = dim

    def __call__(self, input: Documents) -> Embeddings:  # noqa: A002 (chroma signature)
        return [embed_text(t, self.dim) for t in input]

    @staticmethod
    def name() -> str:
        return "sprints-hashing"

    def get_config(self) -> dict:
        return {"dim": self.dim}

    @staticmethod
    def build_from_config(config: dict) -> "HashingEmbeddingFunction":
        return HashingEmbeddingFunction(**config)

    def default_space(self) -> str:
        return "cosine"


def get_embedding_function():
    """Pick the embedding backend from configuration."""
    if config.EMBEDDINGS == "openai":
        if not config.LIVE_CALLS_AUTHORIZED:
            raise PermissionError("Paid embedding calls require explicit authorization")
        from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
        import os

        return OpenAIEmbeddingFunction(api_key=os.environ["OPENAI_API_KEY"], model_name=config.OPENAI_EMBED_MODEL)
    return HashingEmbeddingFunction()


# ------------------------------------------------------------------ ingestion
@dataclass
class IngestReport:
    """Summary returned by :func:`ingest_curriculum`."""

    documents: int
    chunks: int
    max_chunk_tokens: int
    chunk_tokens: int = config.CHUNK_TOKENS
    chunk_overlap: int = config.CHUNK_OVERLAP_TOKENS
    tokenizer: str = field(default_factory=tokenizer_name)
    seconds: float = 0.0


def load_curriculum_documents(directory: Path = config.CURRICULUM_DIR) -> list[Document]:
    """Load every ``.md``/``.txt`` curriculum file as a LangChain ``Document``."""
    docs = []
    for path in sorted(Path(directory).glob("*")):
        if path.suffix.lower() in {".md", ".txt"}:
            docs.append(Document(page_content=path.read_text(encoding="utf-8"), metadata={"source": path.name}))
    if not docs:
        raise FileNotFoundError(f"No curriculum documents found in {directory}")
    return docs


def chunk_documents(docs: list[Document]) -> list[Document]:
    """Split documents into 500-token chunks with a 50-token overlap."""
    # Exact token offsets make the overlap independently auditable.
    enc = _encoder()
    chunks = []
    for doc in docs:
        tokens = enc.encode(doc.page_content, disallowed_special=())
        start, index = 0, 0
        while start < len(tokens):
            end = min(start + config.CHUNK_TOKENS, len(tokens))
            while end > start:
                try:
                    text = enc.decode_bytes(tokens[start:end]).decode("utf-8", errors="strict")
                    if end < len(tokens):
                        enc.decode_bytes(tokens[end-config.CHUNK_OVERLAP_TOKENS:end]).decode("utf-8", errors="strict")
                    break
                except UnicodeDecodeError:
                    end -= 1
            if end <= start + config.CHUNK_OVERLAP_TOKENS and end < len(tokens):
                raise ValueError("Unable to form a valid token window with exact overlap")
            metadata = {**doc.metadata, "chunk_index": index, "tokens": count_tokens(text),
                        "token_start": start, "token_end": end,
                        "overlap_tokens": config.CHUNK_OVERLAP_TOKENS if index else 0}
            if metadata["tokens"] > config.CHUNK_TOKENS:
                raise ValueError("Exact token count exceeded the configured chunk limit")
            chunks.append(Document(page_content=text, metadata=metadata))
            if end == len(tokens):
                break
            start = end - config.CHUNK_OVERLAP_TOKENS
            index += 1
    return chunks


def _client():
    config.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(config.CHROMA_DIR))


def ingest_curriculum(directory: Path = config.CURRICULUM_DIR, reset: bool = True) -> IngestReport:
    """Run the full load -> chunk -> embed -> store pipeline into ChromaDB."""
    t0 = time.perf_counter()
    docs = load_curriculum_documents(directory)
    chunks = chunk_documents(docs)
    client = _client()
    if reset:
        try:
            client.delete_collection(config.CHROMA_COLLECTION)
        except Exception:
            pass
    col = client.get_or_create_collection(
        config.CHROMA_COLLECTION, embedding_function=get_embedding_function(), metadata={"hnsw:space": "cosine"}
    )
    col.add(
        ids=[f"{c.metadata['source']}::{c.metadata['chunk_index']}" for c in chunks],
        documents=[c.page_content for c in chunks],
        metadatas=[c.metadata for c in chunks],
    )
    _collection.cache_clear()
    return IngestReport(
        documents=len(docs), chunks=len(chunks),
        max_chunk_tokens=max(c.metadata["tokens"] for c in chunks),
        seconds=round(time.perf_counter() - t0, 3),
    )


# ------------------------------------------------------------------ retrieval
@lru_cache(maxsize=1)
def _collection():
    client = _client()
    try:
        return client.get_collection(config.CHROMA_COLLECTION, embedding_function=get_embedding_function())
    except Exception:
        ingest_curriculum()
        return _client().get_collection(config.CHROMA_COLLECTION, embedding_function=get_embedding_function())


@dataclass
class RetrievalResult:
    """Chunks returned for one query plus the measured latency."""

    query: str
    chunks: list[dict]
    latency_ms: float

    def to_dict(self) -> dict:
        return asdict(self)


def _query(query: str, k: int) -> list[dict]:
    res = _collection().query(query_texts=[query], n_results=k)
    return [
        {"text": doc, "source": meta["source"], "chunk_index": meta["chunk_index"], "score": round(1.0 - dist, 4)}
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
    ]


def retrieve(query: str, k: int = config.RETRIEVAL_TOP_K, timeout_ms: int = config.RETRIEVAL_TIMEOUT_MS) -> RetrievalResult:
    """Return the top-``k`` curriculum chunks for ``query`` within ``timeout_ms``.

    Raises :class:`RetrievalTimeout` if the budget is exceeded so the Advisor
    can fall back to a structured "Unable to verify" answer.
    """
    t0 = time.perf_counter()
    future = _POOL.submit(_query, query, k)
    try:
        chunks = future.result(timeout=timeout_ms / 1000)
    except FuturesTimeout as exc:
        future.cancel()
        raise RetrievalTimeout(f"ChromaDB query exceeded {timeout_ms} ms") from exc
    latency = (time.perf_counter() - t0) * 1000
    log.debug("retrieve %r -> %d chunks in %.1f ms", query, len(chunks), latency)
    return RetrievalResult(query=query, chunks=chunks, latency_ms=round(latency, 2))


def warm_up() -> float:
    """Prepare client, collection and index before accepting learner requests.

    Returns startup milliseconds. Failure propagates: callers must not advertise
    readiness after a failed warm-up. Cold initialization is never counted as
    a successful sub-second request; benchmark it separately.
    """
    t0 = time.perf_counter()
    # Service construction must fail if initialization/index preparation fails.
    # This is explicit startup work, measured separately from request latency.
    result = retrieve("warm up", k=1, timeout_ms=30000)
    if not result.chunks:
        raise RuntimeError("Curriculum readiness check returned no source chunks")
    return (time.perf_counter() - t0) * 1000


@tool
def search_curriculum(query: str) -> str:
    """Search the Sprints curriculum (Modules 1-5 and career policy) and return the best passages as JSON.

    Use for any learner question about Python grading, LangChain, RAG, LangGraph,
    memory, human-in-the-loop or placement policy. On failure returns an
    'unable_to_verify' JSON object instead of raising.
    """
    import json

    try:
        return json.dumps(retrieve(query).to_dict())
    except Exception as exc:
        return UnableToVerify(source="chroma", message="curriculum search is unavailable", detail=str(exc)).model_dump_json()


if __name__ == "__main__":  # python -m src.tools.rag_retriever
    print(ingest_curriculum())
