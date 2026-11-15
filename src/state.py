"""Global LangGraph state (Sprint 2: unified StateGraph with a TypedDict state).

Only ``messages`` has a reducer (``add_messages``): it accumulates the
HumanMessage / AIMessage / ToolMessage protocol across turns of one learner's
thread. ``turn_count`` and ``last_topic`` are deliberately *not* reset per turn
- they are the persistent per-learner memory. Everything else is per-turn
scratch space reset by the orchestrator node.
"""
from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

Intent = Literal["curriculum_question", "career_match", "grade_code", "unknown"]


class OrchestratorState(TypedDict, total=False):
    # --- protocol + persistent per-learner memory ---
    messages: Annotated[list[AnyMessage], add_messages]
    learner_id: str
    turn_count: int
    last_topic: str
    # --- routing ---
    query: str
    assignment_hint: str
    intent: Intent
    route: Literal["advisor_curriculum", "advisor_career", "assessor", "deny", "clarify"]
    # --- Advisor: agentic RAG ---
    search_query: str
    tried_queries: list[str]
    retrieval_attempts: int
    retrieved: list[dict]
    context_sufficient: bool
    # --- Advisor: career matching ---
    profile: dict
    openings: list[dict]
    recommendation: dict
    requires_approval: bool
    approval: dict
    pending_id: str
    # --- Assessor: evaluator-optimizer ---
    assignment_id: str
    code: str
    evidence: dict
    assessment: dict
    judge: dict
    judge_issues: list[str]
    refinement_count: int
    grader_calls: int
    needs_human_review: bool
    # --- output ---
    status: str
    final_answer: str
    fallback: dict
