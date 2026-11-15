"""Assessor Agent: sandboxed execution + Evaluator-Optimizer grading loop.

Curriculum mapping: Module 1 (rubric, allowed modules), Module 4 (evaluator-optimizer, max 3 refinements),
Module 5 (sandboxing). Flow: run -> grade -> judge -> (approved ? finalize : refine -> grade) with a hard cap.
"""
from __future__ import annotations

import re

from langchain_core.messages import AIMessage

from src import config
from src.protocol import tool_exchange
from src.rubric import ASSIGNMENTS, RUBRIC_TEXT
from src.schemas import UnableToVerify
from src.state import OrchestratorState
from src.tools.code_repl import run_with_tests

_FENCE = re.compile(r"```(?:python|py)?[ \t]*\n(.*?)```", re.S | re.I)


def extract_code(text: str) -> str:
    """Return the first fenced code block in ``text`` ('' if none)."""
    m = _FENCE.search(text)
    return m.group(1).strip("\n") if m else ""


def make_assessor_nodes(reasoner):
    def assessor_run(state: OrchestratorState) -> dict:
        """Execute the submission in the sandbox against the assignment's hidden tests."""
        assignment = ASSIGNMENTS[state["assignment_id"]]
        try:
            evidence = run_with_tests(state["code"], assignment)
        except Exception as exc:
            fb = UnableToVerify(source="python_repl", message="the submission could not be executed safely", detail=str(exc))
            return {"fallback": fb.model_dump(), "messages": tool_exchange("assessor", "execute_python", {"assignment": assignment["id"]}, fb.model_dump_json())}
        if evidence["run"]["status"] == "unable_to_verify":
            fb = UnableToVerify(source="python_repl", message="a verified isolated Python sandbox is unavailable")
            return {"fallback": fb.model_dump(), "messages": tool_exchange("assessor", "execute_python", {"assignment": assignment["id"]}, fb.model_dump_json())}
        summary = {"status": evidence["run"]["status"], "passed": evidence["passed"], "total": evidence["total"],
                   "stderr": evidence["run"]["stderr"][:200], "duration_ms": evidence["run"]["duration_ms"]}
        import json

        return {"evidence": evidence, "refinement_count": 0, "grader_calls": 0, "judge_issues": [],
                "messages": tool_exchange("assessor", "execute_python", {"assignment": assignment["id"], "chars": len(state["code"])}, json.dumps(summary))}

    def assessor_grade(state: OrchestratorState) -> dict:
        """Produce (or refine) the structured grade; the judge's issues from the last round are fed back in."""
        assignment = ASSIGNMENTS[state["assignment_id"]]
        try:
            result = reasoner.grade(assignment, state["code"], state["evidence"], state.get("judge_issues", []), state.get("refinement_count", 0))
        except Exception as exc:
            fb = UnableToVerify(source="grader", message="the grade could not be produced", detail=str(exc))
            return {"fallback": fb.model_dump()}
        calls = state.get("grader_calls", 0) + 1
        return {"assessment": result.model_dump(), "grader_calls": calls,
                "messages": [AIMessage(name="assessor", content=f"Draft grade #{calls}: {result.score}/100 ({result.pass_status})")]}

    def assessor_judge(state: OrchestratorState) -> dict:
        """LLM-as-a-Judge: review the draft grade against the explicit rubric."""
        from src.schemas import AssessmentResult

        assignment = ASSIGNMENTS[state["assignment_id"]]
        try:
            verdict = reasoner.judge(assignment, state["code"], state["evidence"], AssessmentResult(**state["assessment"]))
        except Exception:
            from src.schemas import JudgeVerdict
            verdict = JudgeVerdict(approved=False, issues=["Judge unavailable; grade requires human verification"])
        note = "approved" if verdict.approved else "rejected: " + "; ".join(verdict.issues)
        return {"judge": verdict.model_dump(), "messages": [AIMessage(name="judge", content=f"Judge verdict: {note}")]}

    def assessor_refine(state: OrchestratorState) -> dict:
        """Optimizer step: record the judge's issues and count one refinement."""
        n = state.get("refinement_count", 0) + 1
        return {"refinement_count": n, "judge_issues": state["judge"]["issues"],
                "messages": [AIMessage(name="assessor", content=f"Refinement {n}/{config.MAX_REFINEMENTS}: addressing judge issues.")]}

    def assessor_finalize(state: OrchestratorState) -> dict:
        """Format the learner-facing result; flag for a human grader if the judge never approved."""
        a = state["assessment"]
        flagged = not state["judge"]["approved"]
        if flagged:  # never present an unverified grade as final
            lines = [f"Provisional score: {a['score']}/100 - NOT FINAL (pending review by a Sprints grader)",
                     *[f"- {p}" for p in a["feedback_points"]],
                     f"Note: the automatic judge did not approve this grade after {state.get('refinement_count', 0)} refinements, "
                     "so a Sprints grader will double-check this result before it counts."]
        else:
            lines = [f"Score: {a['score']}/100 - {a['pass_status'].upper()} (pass mark {config.PASS_SCORE})",
                     *[f"- {p}" for p in a["feedback_points"]]]
        return {"final_answer": "\n".join(lines), "needs_human_review": flagged,
                "status": "graded_needs_human_review" if flagged else "graded"}

    return assessor_run, assessor_grade, assessor_judge, assessor_refine, assessor_finalize


def route_after_run(state: OrchestratorState) -> str:
    return "finalize" if state.get("fallback") else "assessor_grade"


def route_after_grade(state: OrchestratorState) -> str:
    return "finalize" if state.get("fallback") else "assessor_judge"


def route_after_judge(state: OrchestratorState) -> str:
    """Approved -> finalize. Otherwise refine, but never beyond MAX_REFINEMENTS (cost/latency cap)."""
    if state["judge"]["approved"] or state.get("refinement_count", 0) >= config.MAX_REFINEMENTS:
        return "assessor_finalize"
    return "assessor_refine"
