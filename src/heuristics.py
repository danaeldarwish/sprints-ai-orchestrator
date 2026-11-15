"""Deterministic offline reasoner.

A rule-based stand-in for the LLM so the whole graph runs, tests and demos with no
API key or network. It implements the same ``Reasoner`` interface as the OpenAI
backend in ``src/llm.py``. The graph structure, tools, sandbox, DB, ChromaDB,
checkpointing and HITL are identical in both modes - only the *language
judgements* (intent, sufficiency, wording of feedback) differ.
"""
from __future__ import annotations

import re

from src import config
from src.rubric import score_breakdown
from src.schemas import AssessmentResult, ContextAssessment, IntentDecision, JudgeVerdict
from src.textutil import content_terms

GLOSSARY = {
    "remember": "memory checkpointer MemorySaver thread ID", "memory": "MemorySaver checkpointer thread ID",
    "forget": "checkpointer thread ID memory", "student": "learner thread", "session": "checkpointer thread ID",
    "pause": "interrupt human-in-the-loop", "approval": "interrupt human-in-the-loop approve", "approve": "interrupt human-in-the-loop",
    "manager": "human reviewer advisor", "sign": "approval interrupt", "human": "human-in-the-loop interrupt",
    "route": "conditional edges orchestrator intent", "routing": "conditional edges orchestrator",
    "split": "chunk overlap", "chunk": "chunk 500-token overlap", "database": "ChromaDB vector", "vector": "ChromaDB embedding",
    "grade": "rubric correctness points", "grading": "rubric correctness points", "score": "rubric correctness points",
    "marks": "rubric points", "retry": "refinement loop judge", "judge": "evaluator-optimizer rubric",
    "loop": "evaluator-optimizer refinement", "secure": "sandbox allow-listed", "safe": "sandbox allow-listed",
    "invent": "hallucination grounding", "fake": "hallucination grounding", "json": "Pydantic parser schema",
    "format": "Pydantic parser schema", "agent": "ReAct tool", "sql": "SQL tool read-only SELECT",
    "fawry": "tier-1 partner approval", "salary": "target salary EGP band", "search": "retrieval query",
}
_CAREER = re.compile(r"\b(placement|job|jobs|opening|openings|hire|hiring|employer|employers|career|salary|match|recommend|apply|"
                     r"fawry|swvl|vodafone|e&|partner|partners|offer)\b", re.I)
_GRADE = re.compile(r"\b(grade|grading|submission|submit|my code|review my code|mark my)\b", re.I)
_SENT = re.compile(r"(?<=[.!?])\s+|\n+")


class HeuristicReasoner:
    """Rule-based implementation of the Reasoner interface (see ``src/llm.py``)."""

    name = "offline-heuristic"

    # ------------------------------------------------------------- routing
    def classify_intent(self, text: str, has_code: bool) -> IntentDecision:
        if has_code or _GRADE.search(text):
            return IntentDecision(intent="grade_code", confidence=0.95 if has_code else 0.7, rationale="code or grading request")
        if _CAREER.search(text):
            return IntentDecision(intent="career_match", confidence=0.8, rationale="career/placement vocabulary")
        if text.strip():
            return IntentDecision(intent="curriculum_question", confidence=0.6, rationale="default for course questions")
        return IntentDecision(intent="unknown", confidence=1.0, rationale="empty message")

    # ------------------------------------------------------ agentic RAG
    def assess_context(self, question: str, search_query: str, chunks: list[dict]) -> ContextAssessment:
        """Sufficient when >= COVERAGE_THRESHOLD of the query's terms appear in the two best chunks."""
        terms = set(content_terms(search_query))
        if not terms or not chunks:
            return ContextAssessment(sufficient=False, reason="no query terms or no chunks")
        have = set(content_terms(" ".join(c["text"] for c in chunks[:2])))
        cov = len(terms & have) / len(terms)
        return ContextAssessment(sufficient=cov >= config.COVERAGE_THRESHOLD,
                                 reason=f"{cov:.0%} of query terms found in top passages (need {config.COVERAGE_THRESHOLD:.0%})")

    def reformulate(self, question: str, tried: list[str]) -> str:
        """Rewrite to curriculum vocabulary using the glossary; fall back to the bare content terms."""
        terms = content_terms(question)
        expansion: list[str] = []
        for t in terms:
            for key, val in GLOSSARY.items():
                if t == content_terms(key)[0]:
                    expansion += val.split()
        seen, out = set(), []
        for w in expansion or terms:
            if w.lower() not in seen:
                seen.add(w.lower())
                out.append(w)
        return " ".join(out)

    def compose_answer(self, question: str, search_query: str, chunks: list[dict], sufficient: bool) -> str:
        if not sufficient or not chunks:
            return ("I could not find that in the Sprints curriculum, so I won't guess. "
                    "Try rephrasing, or ask a Sprints advisor to point you to the right module.")
        q = set(content_terms(question)) | set(content_terms(search_query))
        scored = []
        for rank, c in enumerate(chunks[:3]):
            for pos, raw in enumerate(_SENT.split(c["text"])):
                s = re.sub(r"[#>*`]+|^\s*(?:-|\d+\.)\s*", "", raw).strip()
                if len(s) < 25 or s.startswith("Synthetic"):
                    continue
                overlap = len(q & set(content_terms(s)))
                if overlap:
                    scored.append((overlap, -rank, -pos, s, c["source"]))
        best = sorted(scored, reverse=True)[:3]
        best.sort(key=lambda x: (-x[1], -x[2]))
        body = " ".join(s if s.endswith((".", "!", "?", ":")) else s + "." for _, _, _, s, _ in best)
        sources = ", ".join(dict.fromkeys(src for *_, src in best))
        return f"{body}\n\nSources: {sources}"

    # ---------------------------------------------------- evaluator-optimizer
    def grade(self, assignment: dict, code: str, evidence: dict, judge_issues: list[str], refinement: int) -> AssessmentResult:
        b = score_breakdown(code, evidence)
        run, pts = evidence["run"], []
        pts.append(f"Passed {evidence['passed']}/{evidence['total']} tests (correctness {b['correctness']}/70).")
        for t in [t for t in evidence["tests"] if not t["ok"]][:2]:
            pts.append(f"Test failed for input {t['input']}: expected {t['expected']}, got {t['got']}.")
        if run["status"] != "ok":
            detail = run["stderr"] or "; ".join(run["violations"]) or run["status"]
            pts.append(f"The code did not run cleanly ({run['status']}): {detail}")
        pts += [f"Readability: {n}." for n in b["readability_notes"]]
        if evidence["passed"] == evidence["total"] and run["status"] == "ok" and not b["readability_notes"]:
            pts.append("All tests passed and the code is clean and readable. Excellent work.")
        return AssessmentResult(score=b["score"], feedback_points=pts[:8], pass_status=b["pass_status"])

    def judge(self, assignment: dict, code: str, evidence: dict, result: AssessmentResult) -> JudgeVerdict:
        exp = score_breakdown(code, evidence)
        failing = evidence["passed"] < evidence["total"] or evidence["run"]["status"] != "ok"
        text = " ".join(result.feedback_points).lower()
        claimed = re.findall(r"(\d+)/(\d+) tests", text)
        checks = {
            "score_matches_rubric": result.score == exp["score"],
            "pass_status_correct": result.pass_status == ("pass" if result.score >= config.PASS_SCORE else "fail"),
            "test_counts_grounded": all((int(a), int(b)) == (evidence["passed"], evidence["total"]) for a, b in claimed),
            "failures_mentioned": (not failing) or any(w in text for w in ("fail", "error", "blocked", "timeout", "did not run")),
            "feedback_specific": all(len(p) >= 15 for p in result.feedback_points),
        }
        msgs = {
            "score_matches_rubric": f"score {result.score} does not match rubric arithmetic from the evidence ({exp['score']})",
            "pass_status_correct": f"pass_status '{result.pass_status}' contradicts the pass mark of {config.PASS_SCORE}",
            "test_counts_grounded": f"feedback cites test counts that differ from the evidence ({evidence['passed']}/{evidence['total']})",
            "failures_mentioned": "failing tests or execution errors exist but the feedback does not mention them",
            "feedback_specific": "at least one feedback point is too vague",
        }
        issues = [msgs[k] for k, ok in checks.items() if not ok]
        return JudgeVerdict(approved=not issues, issues=issues, rubric_checks=checks)
