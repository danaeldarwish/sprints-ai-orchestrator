"""Advisor Agent: curriculum Q&A (agentic RAG) and career matching (ReAct SQL agent + HITL).

Curriculum mapping: Module 3 (RAG, self-reflection), Module 2 (ReAct + SQL tools),
Module 5 (human-in-the-loop, grounding), Career Services policy (eligibility, tiers).

Hallucination policy (discovery call): every claim in a career message is rendered from database rows by
``build_career_message`` and re-checked by ``verify_grounding``; no model text reaches the learner about
employers, salaries or qualifications.
"""
from __future__ import annotations

import json
import re
import secrets

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage, HumanMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import interrupt

from src import config
from src.protocol import tool_exchange
from src.schemas import UnableToVerify
from src.state import OrchestratorState
from src.textutil import content_terms
from src.tools.db_queries import DB_TOOLS
from src.tools.rag_retriever import retrieve

REACT_SYSTEM = (
    "You are the Sprints Advisor's database agent. For the learner id given, call get_learner_profile, then "
    "list_matching_openings. Never state facts that are not in tool results. If a tool reports unable_to_verify, stop."
)


# --------------------------------------------------------------- agentic RAG
def make_curriculum_nodes(reasoner):
    """Nodes for the Advisor's agentic RAG loop (retrieve -> reflect -> [reformulate -> retrieve]* -> answer)."""

    def advisor_retrieve(state: OrchestratorState) -> dict:
        """Search ChromaDB for the current search query (<= 1000 ms, else structured fallback)."""
        q = state["search_query"]
        attempts = state.get("retrieval_attempts", 0) + 1
        tried = [*state.get("tried_queries", []), q]
        try:
            res = retrieve(q)
        except Exception as exc:
            fb = UnableToVerify(source="chroma", message="the curriculum search is unavailable", detail=str(exc))
            return {"fallback": fb.model_dump(), "retrieved": [], "retrieval_attempts": attempts, "tried_queries": tried,
                    "messages": tool_exchange("advisor", "search_curriculum", {"query": q}, fb.model_dump_json())}
        brief = json.dumps({"latency_ms": res.latency_ms, "hits": [
            {"source": c["source"], "score": c["score"], "snippet": c["text"][:90].replace("\n", " ")} for c in res.chunks]})
        return {"retrieved": res.chunks, "retrieval_attempts": attempts, "tried_queries": tried,
                "messages": tool_exchange("advisor", "search_curriculum", {"query": q}, brief)}

    def advisor_reflect(state: OrchestratorState) -> dict:
        """Self-reflection: is the retrieved context sufficient to answer the question?"""
        try:
            verdict = reasoner.assess_context(state["query"], state["search_query"], state.get("retrieved", []))
        except Exception:
            return {"fallback": UnableToVerify(source="reasoner", message="context reflection is unavailable").model_dump()}
        return {"context_sufficient": verdict.sufficient,
                "messages": [AIMessage(name="advisor", content=f"Reflection (attempt {state['retrieval_attempts']}): "
                                       f"{'sufficient' if verdict.sufficient else 'insufficient'} - {verdict.reason}")]}

    def advisor_reformulate(state: OrchestratorState) -> dict:
        """Rewrite the query in curriculum vocabulary; stop early if no new query can be produced."""
        tried = state.get("tried_queries", [])
        try:
            new = reasoner.reformulate(state["query"], tried).strip()
        except Exception:
            return {"fallback": UnableToVerify(source="reasoner", message="query reformulation is unavailable").model_dump()}
        seen = [set(content_terms(t)) for t in tried]
        if not new or set(content_terms(new)) in seen:
            return {"retrieval_attempts": config.MAX_RETRIEVAL_ATTEMPTS,
                    "messages": [AIMessage(name="advisor", content="No better query available; stopping search.")]}
        return {"search_query": new, "messages": [AIMessage(name="advisor", content=f"Reformulated query: {new}")]}

    def advisor_answer(state: OrchestratorState) -> dict:
        """Compose an answer strictly from retrieved passages, or say it is not in the curriculum."""
        ok = state.get("context_sufficient", False)
        try:
            text = reasoner.compose_answer(state["query"], state["search_query"], state.get("retrieved", []), ok)
        except Exception:
            return {"fallback": UnableToVerify(source="reasoner", message="answer generation is unavailable").model_dump(), "final_answer": ""}
        update = {"final_answer": text, "status": "answered" if ok else "not_in_curriculum"}
        topic = " ".join(content_terms(state["query"])[:6])
        if topic:  # a vague follow-up ("tell me more") must not erase the remembered topic
            update["last_topic"] = topic
        return update

    return advisor_retrieve, advisor_reflect, advisor_reformulate, advisor_answer


def route_after_retrieve(state: OrchestratorState) -> str:
    return "finalize" if state.get("fallback") else "advisor_reflect"


def route_after_reformulate(state: OrchestratorState) -> str:
    if state.get("fallback"):
        return "finalize"
    """Search again unless reformulation gave up (attempt budget exhausted)."""
    return "advisor_answer" if state.get("retrieval_attempts", 0) >= config.MAX_RETRIEVAL_ATTEMPTS else "advisor_retrieve"


def route_after_reflect(state: OrchestratorState) -> str:
    if state.get("fallback"):
        return "finalize"
    if state.get("context_sufficient") or state.get("retrieval_attempts", 0) >= config.MAX_RETRIEVAL_ATTEMPTS:
        return "advisor_answer"
    return "advisor_reformulate"


# ------------------------------------------------------------- ReAct SQL agent
def build_react_sql_agent(model: BaseChatModel):
    """Simple ReAct agent (agent <-> ToolNode loop) equipped with the SQL tools."""
    bound = model.bind_tools(DB_TOOLS)

    def agent(state: MessagesState) -> dict:
        return {"messages": [bound.invoke(state["messages"])]}

    g = StateGraph(MessagesState)
    g.add_node("agent", agent)
    g.add_node("tools", ToolNode(DB_TOOLS))
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", tools_condition)
    g.add_edge("tools", "agent")
    return g.compile()


# ---------------------------------------------------------------- career flow
def _egp(n: int) -> str:
    return f"{n:,}"


def build_career_message(profile: dict, openings: list[dict]) -> str:
    """Render the learner-facing placement message *only* from database rows (no model text)."""
    ok = [o for o in openings if o["eligible"]]
    no = [o for o in openings if not o["eligible"]]
    lines = [f"Placement review for {profile['name']} ({profile['bootcamp_track']}): {profile['completed_modules']} modules, "
             f"Python score {profile['python_assignment_score']}, target {_egp(profile['target_salary_egp'])} EGP per month."]
    if ok:
        lines.append("Eligible openings:")
        lines += [f"- {o['partner']}: {o['role']} ({o['opening_id']}), salary band {_egp(o['salary_min_egp'])}-{_egp(o['salary_max_egp'])} EGP"
                  for o in ok]
    else:
        lines.append("There are no eligible openings for you right now.")
    if no:
        lines.append("Not matched:")
        lines += [f"- {o['partner']}: {o['role']} ({o['opening_id']}): {'; '.join(o['reasons'])}" for o in no]
    lines.append("These results come from your Sprints records. They are not a job offer.")
    lines.append("Partner openings are synthetic POC seed data.")
    return "\n".join(lines)


def verify_grounding(message: str, profile: dict, openings: list[dict], all_partners: set[str] | None = None) -> list[str]:
    """Return problems if ``message`` mentions a partner, opening ID or number not present in the evidence."""
    problems = []
    evid_partners = {o["partner"] for o in openings}
    known = (all_partners or {"Fawry", "Swvl", "Vodafone Egypt", "e& Egypt"}) | evid_partners
    for p in known - evid_partners:
        if p.lower() in message.lower():
            problems.append(f"mentions partner '{p}' that is not in the learner's retrieved records")
    allowed_ids = {o["opening_id"] for o in openings}
    for oid in set(re.findall(r"OPN-[A-Z]+-[A-Z]+", message)) - allowed_ids:
        problems.append(f"mentions opening '{oid}' that does not exist in the retrieved records")
    allowed_nums = {int(n) for n in re.findall(r"\d+", json.dumps([profile, openings]))}
    for raw in re.findall(r"\d[\d,]*", message):
        n = int(raw.replace(",", ""))
        if n not in allowed_nums:
            problems.append(f"number {raw} does not appear in the retrieved records")
    return problems


def make_career_nodes(react_agent):
    """Nodes for the career flow: ReAct lookup -> deterministic recommendation -> HITL gate -> finalize."""

    def advisor_career(state: OrchestratorState) -> dict:
        """Run the ReAct SQL agent for this learner and extract structured evidence from its ToolMessages."""
        lid = state["learner_id"]
        ask = HumanMessage(content=f"Retrieve the profile and eligible openings for learner {lid}.", name="advisor")
        try:
            out = react_agent.invoke({"messages": [SystemMessage(content=REACT_SYSTEM), ask]}, {"recursion_limit": 12})
        except Exception:
            return {"fallback": UnableToVerify(source="sqlite_agent", message="the bounded database lookup is unavailable").model_dump()}
        new = [m for m in out["messages"] if not isinstance(m, SystemMessage)]
        profile = openings = None
        for m in new:
            if isinstance(m, ToolMessage):
                data = json.loads(m.content)
                if data.get("status") == "unable_to_verify":
                    return {"fallback": data, "messages": new}
                if m.name == "get_learner_profile":
                    profile = data
                elif m.name == "list_matching_openings":
                    openings = data["openings"]
        if profile is None or openings is None:
            fb = UnableToVerify(source="sqlite", message="the learner record could not be retrieved", detail="agent did not return both tool results")
            return {"fallback": fb.model_dump(), "messages": new}
        return {"profile": profile, "openings": openings, "messages": new}

    def career_recommend(state: OrchestratorState) -> dict:
        """Build the grounded recommendation and decide whether a tier-1 partner needs human approval."""
        profile, openings = state["profile"], state["openings"]
        message = build_career_message(profile, openings)
        problems = verify_grounding(message, profile, openings)
        if problems:
            fb = UnableToVerify(source="grounding_check", message="the recommendation failed the grounding check",
                                detail="; ".join(problems))
            return {"fallback": fb.model_dump(), "status": "blocked_ungrounded"}
        eligible = [o for o in openings if o["eligible"]]
        tier1 = sorted({o["partner"] for o in eligible if o["partner"] in config.TIER1_PARTNERS})
        rec = {"learner_id": profile["learner_id"], "learner_name": profile["name"], "message": message,
               "eligible_openings": [o["opening_id"] for o in eligible], "tier1_partners": tier1}
        return {"recommendation": rec, "requires_approval": bool(tier1), "pending_id": secrets.token_hex(24),
                "messages": [AIMessage(name="advisor", content=f"Draft recommendation prepared (grounding check passed; "
                                       f"{len(eligible)} eligible, tier-1 partners: {tier1 or 'none'}).")]}

    def hitl_gate(state: OrchestratorState) -> dict:
        """Pause for a human decision when the recommendation involves a tier-1 partner (LangGraph interrupt).

        No side effects before ``interrupt``: on resume this node re-runs from the top.
        """
        rec = state["recommendation"]
        if not state.get("requires_approval"):
            return {"approval": {"approved": True, "reviewer": "automatic", "note": "no tier-1 partner involved"}}
        decision = interrupt({
            "type": "placement_approval", "learner_id": rec["learner_id"], "learner_name": rec["learner_name"],
            "tier1_partners": rec["tier1_partners"], "eligible_openings": rec["eligible_openings"],
            "draft_message": rec["message"], "question": "Approve releasing this placement recommendation to the learner?"})
        from src.service import ReviewDecision, recommendation_digest
        from src.auth import require_review
        parsed = ReviewDecision.model_validate(decision)
        if parsed.pending_id != state["pending_id"]:
            raise PermissionError("Review does not match the pending recommendation")
        reviewer = require_review(state["pending_id"], recommendation_digest(rec), parsed.model_dump())
        return {"approval": {**parsed.model_dump(), "reviewer": reviewer},
                "messages": [AIMessage(name="human_reviewer", content="Authorized human decision recorded.")]}

    def career_finalize(state: OrchestratorState) -> dict:
        """Release the recommendation if approved, otherwise hold it back from the learner."""
        ap, rec = state["approval"], state["recommendation"]
        if ap.get("approved"):
            tail = f"\n\nApproved by Sprints career advisor ({ap['reviewer']})." if state.get("requires_approval") else ""
            return {"final_answer": rec["message"] + tail, "status": "released" if not tail else "approved_by_human"}
        return {"final_answer": "Your placement recommendation is on hold. A Sprints career advisor will contact you with next steps.",
                "status": "rejected_by_human"}

    return advisor_career, career_recommend, hitl_gate, career_finalize


def route_after_career_lookup(state: OrchestratorState) -> str:
    return "finalize" if state.get("fallback") else "career_recommend"


def route_after_recommend(state: OrchestratorState) -> str:
    return "finalize" if state.get("fallback") else "hitl_gate"
