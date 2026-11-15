"""Learner-scoped SQL regression tests, using actual isolated SQLite rows."""
import json
import sqlite3
import pytest
from src.auth import AuthorizationError
from src.tools import db_queries as db

def invoke(ids,token,tool,**args):
    with ids.bind(token): return json.loads(tool.invoke(args))

def test_profile_returns_actual_modules_salary_employers(identity):
    token=identity.issue_mock_session("learner-1001")
    p=invoke(identity,token,db.get_learner_profile,learner_id="spr-1001")
    assert p["completed_modules"]==12 and p["target_salary_egp"]==30000
    assert p["preferred_employers"]==["Fawry","Swvl"]

@pytest.mark.parametrize("tool",[db.get_learner_profile,db.list_matching_openings])
def test_tool_denies_without_trusted_session(tool):
    assert json.loads(tool.invoke({"learner_id":"SPR-1001"}))["status"]=="unable_to_verify"

@pytest.mark.parametrize("lid",["SPR-1002","SPR-1001' OR 1=1 --","SPR-9999",""])
@pytest.mark.parametrize("tool",[db.get_learner_profile,db.list_matching_openings])
def test_tool_itself_enforces_scope(identity,lid,tool):
    token=identity.issue_mock_session("learner-1001")
    out=invoke(identity,token,tool,learner_id=lid)
    assert out["status"]=="unable_to_verify" and "target_salary_egp" not in out

@pytest.mark.parametrize("query",["SELECT * FROM learners","SELECT target_salary_egp FROM learners WHERE learner_id='SPR-1002'","SELECT COUNT(*) FROM learners","DROP TABLE learners","SELECT 1; DELETE FROM learners","PRAGMA database_list"])
def test_arbitrary_sql_is_disabled_even_with_auth(identity,query):
    token=identity.issue_mock_session("learner-1001")
    assert invoke(identity,token,db.run_readonly_sql,query=query)["status"]=="unable_to_verify"
    assert db.run_readonly_sql not in db.DB_TOOLS

def test_database_error_is_structured(identity,monkeypatch):
    token=identity.issue_mock_session("learner-1001")
    def unavailable(): raise sqlite3.OperationalError("fixture unavailable")
    monkeypatch.setattr(db,"_connect_ro",unavailable)
    for tool in (db.get_learner_profile,db.list_matching_openings):
        assert invoke(identity,token,tool,learner_id="SPR-1001")["status"]=="unable_to_verify"

def test_eligibility_uses_rows_and_known_salary_bands(identity):
    for n in (1001,1025,1004,1021):
        token=identity.issue_mock_session(f"learner-{n}")
        rows=invoke(identity,token,db.list_matching_openings,learner_id=f"SPR-{n}")["openings"]
        matches={o["opening_id"]:o for o in rows}
        if n==1001: assert matches["OPN-FAWR-AAA"]["eligible"]
        if n==1025:
            assert matches["OPN-FAWR-AAA"]["eligible"] and not matches["OPN-SWVL-AAA"]["eligible"]
        if n in (1004,1021): assert not any(o["eligible"] for o in rows)

def test_context_is_removed_after_exception(identity):
    token=identity.issue_mock_session("learner-1001")
    with pytest.raises(RuntimeError):
        with identity.bind(token): raise RuntimeError("fixture")
    assert json.loads(db.get_learner_profile.invoke({"learner_id":"SPR-1001"}))["status"]=="unable_to_verify"
