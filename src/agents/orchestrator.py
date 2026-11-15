"""Orchestrator: the unified LangGraph StateGraph (Sprint 2).

One ``StateGraph(OrchestratorState)`` routes each learner message by intent to the Advisor Agent (curriculum
RAG or career matching) or the Assessor Agent (sandboxed grading), with a MemorySaver checkpointer so every
learner's conversation lives in its own thread. Curriculum mapping: Module 4 (StateGraph, conditional edges,
orchestrator-worker) and Module 5 (checkpointers, thread IDs, interrupt).

The trusted OrchestratorService allocates opaque threads after resolving a mock session.
A learner-supplied ID is never authentication. The compiled graph is an application-internal API.
"""
from __future__ import annotations

import re

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.agents import advisor_agent as adv
from src.agents import assessor_agent as ass
from src.llm import Reasoner, get_react_model, get_reasoner
from src.protocol import traced
from src.rubric import ASSIGNMENTS, detect_assignment
from src.state import OrchestratorState
from src.textutil import content_terms
from src.tools.rag_retriever import warm_up
from src.auth import require_learner

_FOLLOW_UP = re.compile(r"\b(it|that|this|those|them|more|again|why)\b", re.I)

# per-turn scratch fields reset at the start of every turn (memory fields are NOT in this list)
_TURN_RESET = {
    "intent": "unknown", "route": "clarify", "search_query": "", "tried_queries": [], "retrieval_attempts": 0,
    "retrieved": [], "context_sufficient": False, "profile": {}, "openings": [], "recommendation": {},
    "requires_approval": False, "approval": {}, "assignment_id": "", "code": "", "evidence": {}, "assessment": {},
    "judge": {}, "judge_issues": [], "refinement_count": 0, "grader_calls": 0, "needs_human_review": False,
    "status": "", "final_answer": "", "fallback": {}, "assignment_hint": "",
}


def thread_config(learner_id: str) -> dict:
    """Removed insecure public helper. Use OrchestratorService with a session."""
    raise PermissionError("Caller-selected learner/thread IDs are not authentication; use OrchestratorService")


def make_orchestrator(reasoner: Reasoner):
    def orchestrator(state: OrchestratorState) -> dict:
        """Classify the newest learner message and choose the worker route (plus privacy and input guards)."""
        text = next((str(m.content) for m in reversed(state["messages"]) if isinstance(m, HumanMessage)), "")
        lid = (state.get("learner_id") or "").upper()
        require_learner(lid)
        hint = state.get("assignment_hint", "")
        code = ass.extract_code(text)
        try:
            decision = reasoner.classify_intent(text, bool(code))
        except Exception:
            from src.schemas import UnableToVerify
            return {**_TURN_RESET, "route": "clarify", "query": text, "fallback": UnableToVerify(source="reasoner", message="intent classification is unavailable").model_dump()}
        update = {**_TURN_RESET, "query": text, "intent": decision.intent, "turn_count": state.get("turn_count", 0) + 1}
        others = {i.upper() for i in re.findall(r"SPR-\d+", text, re.I)} - {lid}

        if others:
            update |= {"route": "deny", "status": "denied",
                       "final_answer": f"I can only access your own Sprints record ({lid or 'unknown learner'}). "
                                       "I can't share information about other learners."}
        elif decision.intent == "grade_code":
            aid = detect_assignment(code, text, hint)
            if not code or not aid:
                options = " or ".join(ASSIGNMENTS)
                update |= {"route": "clarify", "status": "needs_clarification",
                           "final_answer": f"Please send your code in a ```python block and tell me which assignment it is for ({options})."}
            else:
                update |= {"route": "assessor", "code": code, "assignment_id": aid}
        elif decision.intent == "career_match":
            if not lid:
                update |= {"route": "clarify", "status": "needs_clarification", "final_answer": "Please tell me your learner ID (e.g. SPR-1001)."}
            else:
                update["route"] = "advisor_career"
        elif decision.intent == "curriculum_question":
            query = text
            if state.get("last_topic") and len(content_terms(text)) <= 3 and _FOLLOW_UP.search(text):
                query = f"{state['last_topic']} {text}"
            update |= {"route": "advisor_curriculum", "search_query": query}
        else:
            update |= {"route": "clarify", "status": "needs_clarification",
                       "final_answer": "I can answer curriculum questions, grade a Python submission, or review your placement options. What would you like?"}
        update["messages"] = [AIMessage(name="orchestrator", content=f"Routing: intent={update['intent']} -> {update['route']}")]
        return update

    return orchestrator


def finalize(state: OrchestratorState) -> dict:
    """Emit the learner-facing AIMessage; convert any tool failure into the structured 'Unable to verify' reply."""
    fb = state.get("fallback")
    if fb:
        from src.schemas import UnableToVerify

        text = UnableToVerify(**fb).text()
        return {"final_answer": text, "status": "unable_to_verify", "messages": [AIMessage(name="orchestrator", content=text)]}
    return {"messages": [AIMessage(name="orchestrator", content=state["final_answer"])]}


def route_from_orchestrator(state: OrchestratorState) -> str:
    return {"advisor_curriculum": "advisor_retrieve", "advisor_career": "advisor_career",
            "assessor": "assessor_run"}.get(state["route"], "finalize")


def build_graph(reasoner: Reasoner | None = None, react_model=None, checkpointer=None, warm: bool = True):
    """Compile the full multi-agent graph. Pass fakes for ``reasoner``/``react_model`` in tests."""
    reasoner = reasoner or get_reasoner()
    react = adv.build_react_sql_agent(react_model or get_react_model())
    retrieve_n, reflect_n, reform_n, answer_n = adv.make_curriculum_nodes(reasoner)
    career_n, recommend_n, hitl_n, career_fin_n = adv.make_career_nodes(react)
    run_n, grade_n, judge_n, refine_n, assess_fin_n = ass.make_assessor_nodes(reasoner)

    g = StateGraph(OrchestratorState)
    nodes = {"orchestrator": make_orchestrator(reasoner), "advisor_retrieve": retrieve_n, "advisor_reflect": reflect_n,
             "advisor_reformulate": reform_n, "advisor_answer": answer_n, "advisor_career": career_n,
             "career_recommend": recommend_n, "hitl_gate": hitl_n, "career_finalize": career_fin_n,
             "assessor_run": run_n, "assessor_grade": grade_n, "assessor_judge": judge_n, "assessor_refine": refine_n,
             "assessor_finalize": assess_fin_n, "finalize": finalize}
    for name, fn in nodes.items():
        g.add_node(name, traced(name)(fn))

    g.add_edge(START, "orchestrator")
    g.add_conditional_edges("orchestrator", route_from_orchestrator,
                            ["advisor_retrieve", "advisor_career", "assessor_run", "finalize"])
    # Advisor: agentic RAG with self-reflection loop
    g.add_conditional_edges("advisor_retrieve", adv.route_after_retrieve, ["advisor_reflect", "finalize"])
    g.add_conditional_edges("advisor_reflect", adv.route_after_reflect, ["advisor_answer", "advisor_reformulate", "finalize"])
    g.add_conditional_edges("advisor_reformulate", adv.route_after_reformulate, ["advisor_retrieve", "advisor_answer", "finalize"])
    g.add_edge("advisor_answer", "finalize")
    # Advisor: career matching + human-in-the-loop
    g.add_conditional_edges("advisor_career", adv.route_after_career_lookup, ["career_recommend", "finalize"])
    g.add_conditional_edges("career_recommend", adv.route_after_recommend, ["hitl_gate", "finalize"])
    g.add_edge("hitl_gate", "career_finalize")
    g.add_edge("career_finalize", "finalize")
    # Assessor: evaluator-optimizer loop
    g.add_conditional_edges("assessor_run", ass.route_after_run, ["assessor_grade", "finalize"])
    g.add_conditional_edges("assessor_grade", ass.route_after_grade, ["assessor_judge", "finalize"])
    g.add_conditional_edges("assessor_judge", ass.route_after_judge, ["assessor_finalize", "assessor_refine"])
    g.add_edge("assessor_refine", "assessor_grade")
    g.add_edge("assessor_finalize", "finalize")
    g.add_edge("finalize", END)

    if warm:
        warm_up()
    return g.compile(checkpointer=checkpointer or MemorySaver())
