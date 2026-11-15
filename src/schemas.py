"""Pydantic schemas shared by agents, parsers and tests.

Sprint 1 scope: ``AssessmentResult`` is the strict JSON contract for the
Assessor Agent's feedback (score, feedback_points, pass_status).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class AssessmentResult(BaseModel):
    """Assessor Agent output for one Python assignment (curriculum: Module 1 grading rubric)."""

    score: int = Field(ge=0, le=100, description="Total rubric score 0-100.")
    feedback_points: list[str] = Field(
        min_length=1, max_length=8,
        description="Specific, evidence-based feedback. Cite test counts or error types.",
    )
    pass_status: Literal["pass", "fail"] = Field(description="'pass' when score >= the pass mark.")


class JudgeVerdict(BaseModel):
    """LLM-as-a-Judge review of an AssessmentResult against the explicit rubric."""

    approved: bool
    issues: list[str] = Field(default_factory=list)
    rubric_checks: dict[str, bool] = Field(default_factory=dict)


class IntentDecision(BaseModel):
    """Orchestrator routing decision."""

    intent: Literal["curriculum_question", "career_match", "grade_code", "unknown"]
    confidence: float = Field(ge=0, le=1, default=0.5)
    rationale: str = ""


class ContextAssessment(BaseModel):
    """Advisor self-reflection: is the retrieved context enough to answer?"""

    sufficient: bool
    reason: str = ""


class UnableToVerify(BaseModel):
    """Structured graceful-degradation payload (acceptance criterion)."""

    status: Literal["unable_to_verify"] = "unable_to_verify"
    source: str = Field(description="Which dependency failed: sqlite | python_repl | chroma | learner_record")
    message: str = "Unable to verify"
    detail: str = ""

    def text(self) -> str:
        return f"Unable to verify: {self.message} (source: {self.source})."
