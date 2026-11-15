"""Optimizer control-flow tests with explicit execution FIXTURES, never live grading."""
import pytest
from src.heuristics import HeuristicReasoner
from src.schemas import AssessmentResult
from src.service import OrchestratorService
from src.main import BUGGY,FIXED

def execution_fixture(code,assignment):
    """Known test fixture, not obtained by executing submitted Python."""
    passing=code==FIXED.split("python\n",1)[1].rsplit("```",1)[0].strip("\n")
    tests=[{"ok":passing,"input":repr(a),"expected":repr(e),"got":repr(e) if passing else "fixture failure"} for a,e in assignment["cases"]]
    return {"run":{"status":"ok","stderr":"","stdout":"","violations":[],"duration_ms":0,"exit_code":0},
            "tests":tests,"passed":len(tests) if passing else 0,"total":len(tests),"evidence_kind":"mock_execution_fixture"}

class Counting(HeuristicReasoner):
    def __init__(self): self.calls=0; self.judge_calls=0
    def grade(self,*a,**k):
        self.calls+=1; return super().grade(*a,**k)
    def judge(self,*a,**k):
        self.judge_calls+=1; return super().judge(*a,**k)
class Inflater(Counting):
    def grade(self,*args):
        self.calls+=1
        return AssessmentResult(score=100,feedback_points=["Passed 6/6 tests. Fixture inflated score."],pass_status="pass")
class LearnsFromJudge(Counting):
    def grade(self,assignment,code,evidence,judge_issues,refinement):
        if not judge_issues:
            self.calls+=1
            return AssessmentResult(score=100,feedback_points=["Passed 6/6 tests. Fixture inflated score."],pass_status="pass")
        return super().grade(assignment,code,evidence,judge_issues,refinement)

def run_fixture(identity,monkeypatch,reasoner,text):
    from src.agents import assessor_agent
    monkeypatch.setattr(assessor_agent,"run_with_tests",execution_fixture)
    app=OrchestratorService(identity,reasoner=reasoner,warm=False)
    token=identity.issue_mock_session("learner-1005")
    return app.ask(token,{"text":text})

def test_honest_grader_approved_first_time(identity,monkeypatch):
    reasoner=Counting(); out=run_fixture(identity,monkeypatch,reasoner,FIXED)
    assert (reasoner.calls,reasoner.judge_calls,out["refinement_count"],out["status"])==(1,1,0,"graded")

def test_judge_detects_inflation_and_refines(identity,monkeypatch):
    reasoner=LearnsFromJudge(); out=run_fixture(identity,monkeypatch,reasoner,BUGGY)
    assert out["refinement_count"]==1 and out["status"]=="graded"
    assert out["assessment"]["score"]<100 and out["assessment"]["pass_status"]=="fail"

def test_hard_maximum_three_refinements(identity,monkeypatch):
    reasoner=Inflater(); out=run_fixture(identity,monkeypatch,reasoner,BUGGY)
    assert out["refinement_count"]==3 and reasoner.calls==4 and reasoner.judge_calls==4
    assert out["status"]=="graded_needs_human_review" and "NOT FINAL" in out["final_answer"]

def test_judge_failure_does_not_release_final_grade(identity,monkeypatch):
    class Broken(Counting):
        def judge(self,*args): raise RuntimeError("judge fixture unavailable")
    out=run_fixture(identity,monkeypatch,Broken(),BUGGY)
    assert out["status"]=="graded_needs_human_review" and out["refinement_count"]==3

def test_grader_failure_is_structured(identity,monkeypatch):
    class Broken(Counting):
        def grade(self,*args): raise RuntimeError("grader fixture unavailable")
    out=run_fixture(identity,monkeypatch,Broken(),BUGGY)
    assert out["status"]=="unable_to_verify" and out["fallback"]["source"]=="grader"
