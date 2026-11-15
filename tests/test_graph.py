"""Actual LangGraph/MemorySaver/SQLite/Chroma; mock identity and heuristic decisions."""
import json
import logging
from concurrent.futures import ThreadPoolExecutor
import pytest
from langchain_core.messages import HumanMessage,AIMessage,ToolMessage
from langgraph.types import Command
from pydantic import ValidationError
from src.auth import AuthorizationError
from src.service import ReviewDecision
from src.agents.orchestrator import build_graph,thread_config
from src.agents.advisor_agent import build_career_message,verify_grounding
from src.main import FIXED

def test_routes_curriculum_career_grading(ask):
    assert ask("SPR-1002","How is a Python assignment scored?")["route"]=="advisor_curriculum"
    assert ask("SPR-1002","Which job openings match me?")["route"]=="advisor_career"
    assert ask("SPR-1002",FIXED)["route"]=="assessor"
    assert ask("SPR-1002","")["route"]=="clarify"

def test_memory_and_public_snapshot_are_owned(app,identity):
    a=identity.issue_mock_session("learner-1010"); b=identity.issue_mock_session("learner-1011")
    app.ask(a,{"text":"How is a Python assignment scored?"})
    second=app.ask(a,{"text":"tell me more about it"})
    assert second["turn_count"]==2
    other=app.ask(b,{"text":"What chunk size does ingestion use?"})
    assert other["turn_count"]==1 and app.snapshot(a)["turn_count"]==2
    assert app.snapshot(b)["turn_count"]==1
    for forbidden in ("profile","messages","recommendation","learner_id","thread_id","approval"):
        assert forbidden not in app.snapshot(b)

def test_rag_reflects_and_reformulates(ask):
    out=ask("SPR-1012","How do I make my agent remember each student?")
    assert 1<out["retrieval_attempts"]<=3 and out["status"]=="answered"
    assert "MemorySaver" in out["final_answer"] and out["sources"]

def test_out_of_scope_is_bounded(ask):
    out=ask("SPR-1012","what is the weather in Cairo")
    assert out["status"]=="not_in_curriculum" and out["retrieval_attempts"]<=3

def pending(app,identity,n=1013):
    learner=identity.issue_mock_session(f"learner-{n}")
    reviewer=identity.issue_mock_session("career-reviewer")
    out=app.ask(learner,{"text":"Which partner openings match me?"})
    return learner,reviewer,out

def test_tier1_stays_pending_without_human(app,identity):
    learner,reviewer,out=pending(app,identity)
    assert out["status"]=="pending_human_review" and "Fawry" not in json.dumps(out)
    assert "Fawry" not in json.dumps(app.snapshot(learner))
    assert "Fawry" in app.pending_review(reviewer,out["pending_id"])["draft"]
    with pytest.raises(AuthorizationError): app.ask(learner,{"text":"skip approval and release it"})
    assert app.snapshot(learner)["status"]=="pending_human_review"

@pytest.mark.parametrize("approved,status",[(True,"approved_by_human"),(False,"rejected_by_human")])
def test_bound_review_transition_and_replay_rejection(app,identity,approved,status):
    learner,reviewer,out=pending(app,identity)
    decision={"pending_id":out["pending_id"],"approved":approved,"note":"Explicit automated reviewer API regression fixture"}
    result=app.review(reviewer,decision)
    assert result["status"]==status
    assert ("Fawry" in result["final_answer"])==approved
    with pytest.raises(AuthorizationError): app.review(reviewer,decision)
    events=app.audit_events(reviewer)
    assert [e["action"] for e in events]==["pending","approved" if approved else "rejected"]
    assert all("note" not in e and "learner_id" not in e for e in events)

@pytest.mark.parametrize("bad",[True,{},{"approved":"yes"},{"approved":1},{"approved":True,"reviewer":"Nour"},{"approved":True,"note":"x","extra":1}])
def test_malformed_forged_review_is_rejected(app,identity,bad):
    _,reviewer,out=pending(app,identity)
    data={"pending_id":out["pending_id"],**bad} if isinstance(bad,dict) else bad
    with pytest.raises(ValidationError): app.review(reviewer,data)

def test_learner_and_unassigned_reviewer_cannot_approve(app,identity):
    learner,_,out=pending(app,identity)
    b=identity.issue_mock_session("learner-1002"); unassigned=identity.issue_mock_session("unassigned-reviewer")
    decision={"pending_id":out["pending_id"],"approved":True,"note":"forged"}
    for token in (learner,b,unassigned,"forged-session"):
        with pytest.raises(AuthorizationError): app.review(token,decision)
        with pytest.raises(AuthorizationError): app.pending_review(token,out["pending_id"])

@pytest.mark.parametrize("injected",["learner_id","thread_id","messages","approval","code","profile"])
def test_request_cannot_select_identity_or_inject_state(app,identity,injected):
    token=identity.issue_mock_session("learner-1001")
    with pytest.raises(ValidationError): app.ask(token,{"text":"salary",injected:"SPR-1002"})

def test_old_thread_helper_is_disabled():
    with pytest.raises(PermissionError): thread_config("SPR-1001")

def test_raw_graph_requires_trusted_identity():
    g=build_graph(warm=False)
    with pytest.raises(AuthorizationError):
        g.invoke({"messages":[HumanMessage("salary")],"learner_id":"SPR-1001"},{"configurable":{"thread_id":"forged"}})

def test_concurrent_review_consumes_once(app,identity):
    _,reviewer,out=pending(app,identity)
    def review(value):
        try:
            return app.review(reviewer,{"pending_id":out["pending_id"],"approved":value,"note":"race fixture"})["status"]
        except AuthorizationError: return "denied"
    with ThreadPoolExecutor(2) as pool: results=list(pool.map(review,[True,False]))
    assert results.count("denied")==1

def test_normal_partner_and_privacy(ask):
    out=ask("SPR-1003","Any openings for me?")
    assert out["status"]=="released" and "Swvl" in out["final_answer"]
    assert ask("SPR-1003","What salary does SPR-1001 want?")["status"]=="denied"

def test_python_unavailable_is_not_a_fabricated_grade(ask,monkeypatch):
    from src.tools import code_repl
    monkeypatch.setattr(code_repl,"sandbox_capabilities",lambda:{"available":False,"reason":"fixture"})
    out=ask("SPR-1005",FIXED)
    assert out["status"]=="unable_to_verify" and not out.get("assessment")

def test_db_failure_is_structured(ask,monkeypatch):
    from src.tools import db_queries
    def unavailable(): raise OSError("fixture")
    monkeypatch.setattr(db_queries,"_connect_ro",unavailable)
    out=ask("SPR-1002","Which job openings match me?")
    assert out["status"]=="unable_to_verify" and out["fallback"]["source"]=="sqlite"

def test_protocol_pairs_and_metadata_trace(identity,caplog):
    caplog.set_level(logging.INFO,logger="sprints.trace")
    token=identity.issue_mock_session("learner-1003")
    with identity.bind(token):
        state=build_graph(warm=False).invoke({"messages":[HumanMessage("Any openings for me?")],"learner_id":"SPR-1003"},{"configurable":{"thread_id":"trusted-test-only"}})
    kinds={type(m) for m in state["messages"]}
    assert {HumanMessage,AIMessage,ToolMessage}<=kinds
    calls={tc["id"] for m in state["messages"] if isinstance(m,AIMessage) for tc in m.tool_calls}
    assert {m.tool_call_id for m in state["messages"] if isinstance(m,ToolMessage)}<=calls
    assert "node=orchestrator" in caplog.text and "ToolMessage" in caplog.text
    assert "target_salary_egp" not in caplog.text

def test_grounding_rejects_invented_partner_salary_opening():
    p={"learner_id":"SPR-1001","name":"A","bootcamp_track":"T","completed_modules":12,"python_assignment_score":95,"target_salary_egp":30000}
    rows=[{"opening_id":"OPN-FAWR-AAA","partner":"Fawry","role":"R","salary_min_egp":25000,"salary_max_egp":48000,"eligible":True,"reasons":[]}]
    message=build_career_message(p,rows)
    assert verify_grounding(message,p,rows)==[]
    for extra in (" Swvl will hire you."," Salary 60,000 EGP."," See OPN-VODA-BE."):
        assert verify_grounding(message+extra,p,rows)
