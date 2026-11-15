"""Authenticated application boundary over the private LangGraph/checkpointer.

Raw graph state, ToolMessages and review drafts are application-internal.
Only a scoped reviewer sees a pending draft. Sessions and locks are in-memory.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import secrets
import threading

from langchain_core.messages import HumanMessage
from langgraph.types import Command
from pydantic import BaseModel, ConfigDict, Field

from src.auth import AuthorizationError, MockIdentityProvider


class LearnerRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    text: str = Field(max_length=24000)
    assignment_hint: str = ""


class ReviewDecision(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    pending_id: str = Field(min_length=32, max_length=80)
    approved: bool
    note: str = Field(min_length=1, max_length=500)


def recommendation_digest(rec: dict) -> str:
    return hashlib.sha256(json.dumps(rec, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class OrchestratorService:
    """Public POC API. No caller-controlled checkpoint configuration accepted."""

    def __init__(self, identities: MockIdentityProvider, **graph_options):
        from src.agents.orchestrator import build_graph
        self.__identities = identities
        self.__graph = build_graph(**graph_options)
        self.__threads: dict[str, str] = {}
        self.__pending: dict[str, dict] = {}
        self.__closed: set[str] = set()
        self.__audit: list[dict] = []
        # Serialize state changes including consumption and resume atomically.
        self.__lock = threading.RLock()

    def __config(self, p):
        tid = self.__threads.setdefault(p.subject, secrets.token_hex(24))
        return {"configurable": {"thread_id": tid}, "recursion_limit": 80}

    def __event(self, action, pending_id, role):
        self.__audit.append({"at": datetime.now(timezone.utc).isoformat(), "action": action,
                             "pending_id": pending_id, "actor_role": role})

    @staticmethod
    def __public(state: dict) -> dict:
        # Explicit allowlist: never return raw state, drafts, profiles or tool logs.
        result = {"status": state.get("status", ""), "route": state.get("route", ""),
                  "final_answer": state.get("final_answer", ""), "turn_count": state.get("turn_count", 0)}
        for key in ("assessment", "refinement_count", "grader_calls", "needs_human_review", "retrieval_attempts"):
            if key in state:
                result[key] = state[key]
        if state.get("fallback"):
            result["fallback"] = {"status": "unable_to_verify", "source": state["fallback"].get("source", "application"),
                                  "message": "Unable to verify"}
        if state.get("retrieved"):
            result["sources"] = sorted({c["source"] for c in state["retrieved"]})
        return result

    def ask(self, session: str, request: LearnerRequest | dict) -> dict:
        request = LearnerRequest.model_validate(request)
        with self.__lock, self.__identities.bind(session) as p:
            if p.role != "learner":
                raise AuthorizationError("A learner session is required")
            cfg = self.__config(p)
            if self.__graph.get_state(cfg).next:
                raise AuthorizationError("A human review is pending; this thread cannot be changed")
            state = self.__graph.invoke({"messages": [HumanMessage(request.text)], "learner_id": p.learner_id,
                                        "assignment_hint": request.assignment_hint}, cfg)
            if state.get("__interrupt__"):
                pid = state["pending_id"]
                self.__pending[pid] = {"owner": p.subject, "learner_id": p.learner_id, "config": cfg,
                                       "digest": recommendation_digest(state["recommendation"])}
                self.__event("pending", pid, p.role)
                return {"status": "pending_human_review", "route": "advisor_career", "pending_id": pid,
                        "final_answer": "Your placement recommendation is pending an authorized human review.",
                        "turn_count": state.get("turn_count", 0)}
            return self.__public(state)

    def snapshot(self, session: str) -> dict:
        with self.__lock, self.__identities.bind(session) as p:
            if p.role != "learner":
                raise AuthorizationError("A learner session is required")
            cfg = self.__config(p)
            state = self.__graph.get_state(cfg)
            if state.next:
                return {"status": "pending_human_review", "final_answer": "Pending authorized human review."}
            return self.__public(state.values)

    def pending_review(self, reviewer_session: str, pending_id: str) -> dict:
        with self.__lock, self.__identities.bind(reviewer_session) as p:
            record = self.__pending.get(pending_id)
            if not record or p.role != "reviewer" or record["learner_id"] not in p.review_scope:
                raise AuthorizationError("Review is unavailable or outside reviewer scope")
            state = self.__graph.get_state(record["config"]).values
            return {"pending_id": pending_id, "draft": state["recommendation"]["message"]}

    def review(self, reviewer_session: str, decision: ReviewDecision | dict) -> dict:
        decision = ReviewDecision.model_validate(decision)
        with self.__lock:
            p = self.__identities.resolve(reviewer_session)
            record = self.__pending.get(decision.pending_id)
            if not record or decision.pending_id in self.__closed or p.role != "reviewer" or record["learner_id"] not in p.review_scope:
                raise AuthorizationError("Review is unavailable, consumed or outside reviewer scope")
            snap = self.__graph.get_state(record["config"])
            if snap.next != ("hitl_gate",) or recommendation_digest(snap.values["recommendation"]) != record["digest"]:
                raise AuthorizationError("Pending action changed; explicit new review required")
            payload = decision.model_dump()
            cap = {"pending_id": decision.pending_id, "digest": record["digest"], "decision": payload}
            # Consume before resume. Infrastructure failure requires manual recovery,
            # never silently retry an approval or accept the same decision again.
            self.__closed.add(decision.pending_id)
            self.__pending.pop(decision.pending_id)
            with self.__identities.bind(reviewer_session, review=cap):
                try:
                    result = self.__graph.invoke(Command(resume=payload), record["config"])
                except Exception:
                    self.__event("resume_failed_closed", decision.pending_id, p.role)
                    raise
            self.__event("approved" if decision.approved else "rejected", decision.pending_id, p.role)
            return self.__public(result)

    def audit_events(self, reviewer_session: str) -> list[dict]:
        p = self.__identities.resolve(reviewer_session)
        if p.role != "reviewer":
            raise AuthorizationError("Reviewer session required")
        # Events omit learner identity, text, decisions notes and bearer tokens.
        with self.__lock:
            return [dict(e) for e in self.__audit]
