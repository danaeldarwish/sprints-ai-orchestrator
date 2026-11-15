"""Central configuration for the Sprints AI Career & Assessment Orchestrator.

Every tunable that the client brief or the discovery call fixes (chunk sizes,
latency budget, refinement cap, tier-1 partners, sandbox limits) lives here so
reviewers can audit them in one place.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
CURRICULUM_DIR = DATA_DIR / "curriculum_docs"
LEARNER_CSV = DATA_DIR / "sprints_learner_db.csv"
LEARNER_DB = Path(os.getenv("SPRINTS_DB_PATH", DATA_DIR / "sprints_learner.db"))
CHROMA_DIR = Path(os.getenv("SPRINTS_CHROMA_DIR", ROOT / ".chroma"))
CHROMA_COLLECTION = "sprints_curriculum"

# --- Sprint 1: ingestion / RAG (brief: 500-token chunks, 50-token overlap) ---
CHUNK_TOKENS = 500
CHUNK_OVERLAP_TOKENS = 50
RETRIEVAL_TOP_K = 4
RETRIEVAL_TIMEOUT_MS = 1000          # acceptance criterion: retrieve within 1000 ms
MAX_RETRIEVAL_ATTEMPTS = 3           # self-reflection loop cap (initial + 2 rewrites)
COVERAGE_THRESHOLD = 0.6             # offline reflection: share of query terms found in context

# --- Sprint 2: evaluator-optimizer (brief: halt after max 3 refinements) ---
MAX_REFINEMENTS = 3
PASS_SCORE = 70

# --- Human-in-the-loop: placements to these partners need human approval ---
TIER1_PARTNERS = frozenset({"Fawry"})

# --- Python sandbox limits (discovery call: "strictly sandboxed") ---
SANDBOX_TIMEOUT_S = 5.0
SANDBOX_MEMORY_MB = 512
SANDBOX_MAX_OUTPUT_CHARS = 4000
SANDBOX_MAX_CODE_CHARS = 20000

# --- Model selection ---
LLM_PROVIDER = os.getenv("SPRINTS_LLM", "offline")          # offline | openai
EMBEDDINGS = os.getenv("SPRINTS_EMBEDDINGS", "hashing")     # hashing | openai
OPENAI_CHAT_MODEL = os.getenv("SPRINTS_OPENAI_MODEL", "gpt-6-luna")
OPENAI_EMBED_MODEL = os.getenv("SPRINTS_OPENAI_EMBED_MODEL", "text-embedding-3-small")
LIVE_CALLS_AUTHORIZED = os.getenv("SPRINTS_LIVE_AUTHORIZED", "0") == "1"
