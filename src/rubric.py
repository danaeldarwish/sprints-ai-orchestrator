"""Assignments, the explicit grading rubric and its deterministic scorer.

The rubric below is the same one published in curriculum Module 1, so the grader,
the LLM judge and the learner all see identical criteria.
"""
from __future__ import annotations

import re

from src import config

ASSIGNMENTS: dict[str, dict] = {
    "fizzbuzz": {
        "id": "fizzbuzz", "kind": "stdout", "title": "FizzBuzz",
        "prompt": "Print the numbers 1 to 15, one per line. Print Fizz for multiples of 3, Buzz for multiples of 5, FizzBuzz for both.",
        "expected_stdout": ["1", "2", "Fizz", "4", "Buzz", "Fizz", "7", "8", "Fizz", "Buzz", "11", "Fizz", "13", "14", "FizzBuzz"],
        "keywords": ["fizz", "buzz"],
    },
    "clean_scores": {
        "id": "clean_scores", "kind": "function", "function": "clean_scores", "title": "Clean scores",
        "prompt": "Implement clean_scores(scores) returning the mean of the non-None, non-negative scores rounded to 2 decimals; return 0.0 when none are valid.",
        "cases": [(([80, None, 90],), 85.0), (([],), 0.0), (([100, -5, 50],), 75.0), (([None, None],), 0.0),
                  (([70, 71, 72],), 71.0), (([0, 100],), 50.0)],
        "keywords": ["clean_scores"],
    },
}

RUBRIC = {"correctness": 70, "execution_hygiene": 15, "readability": 15}
RUBRIC_TEXT = (
    "Score out of 100. Correctness (70): proportion of hidden tests passed x 70. Execution hygiene (15): 15 if the code "
    "ran without runtime error, timeout, syntax error or blocked operation, else 0. Readability (15): docstring 5, "
    f"all lines <= 100 chars 5, no bare except / wildcard import 5. Pass mark {config.PASS_SCORE}."
)


def detect_assignment(code: str, text: str = "", explicit: str | None = None) -> str | None:
    """Pick the assignment id from an explicit id, the message text or the code."""
    if explicit in ASSIGNMENTS:
        return explicit
    hay = f"{text}\n{code}".lower()
    for aid, a in ASSIGNMENTS.items():
        if aid in hay or any(k in hay for k in a["keywords"]):
            return aid
    return None


def readability_points(code: str) -> tuple[int, list[str]]:
    """Return (points out of 15, notes) from simple static checks."""
    pts, notes = 0, []
    if re.search(r'^\s*(?:def|class)\s[^\n]*:\s*\n\s*(?:"""|\'\'\')', code, re.M) or code.lstrip().startswith(('"""', "'''")):
        pts += 5
    else:
        notes.append("add a docstring explaining what the code does (-5)")
    if all(len(ln) <= 100 for ln in code.splitlines()):
        pts += 5
    else:
        notes.append("keep lines under 100 characters (-5)")
    if re.search(r"^\s*except\s*:", code, re.M) or re.search(r"import\s+\*", code):
        notes.append("avoid bare 'except:' and wildcard imports (-5)")
    else:
        pts += 5
    return pts, notes


def score_breakdown(code: str, evidence: dict) -> dict:
    """Deterministic rubric score from execution evidence. Used by the offline grader and the judge."""
    total = max(evidence["total"], 1)
    correctness = round(RUBRIC["correctness"] * evidence["passed"] / total)
    hygiene = RUBRIC["execution_hygiene"] if evidence["run"]["status"] == "ok" else 0
    read, notes = readability_points(code)
    score = correctness + hygiene + read
    return {"correctness": correctness, "execution_hygiene": hygiene, "readability": read,
            "score": score, "readability_notes": notes,
            "pass_status": "pass" if score >= config.PASS_SCORE else "fail"}
