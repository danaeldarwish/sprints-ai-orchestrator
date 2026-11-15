"""Strongly typed prompt templates + Pydantic output parsers (Sprint 1).

Each prompt is a ``ChatPromptTemplate`` whose ``{format_instructions}`` come from a
``PydanticOutputParser`` so the model's reply is validated into a schema from
``src.schemas``. Curriculum mapping: Module 2 (prompt templates, structured output).
"""
from __future__ import annotations

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.rubric import RUBRIC_TEXT
from src.schemas import AssessmentResult, ContextAssessment, IntentDecision, JudgeVerdict

ASSESSMENT_PARSER = PydanticOutputParser(pydantic_object=AssessmentResult)
JUDGE_PARSER = PydanticOutputParser(pydantic_object=JudgeVerdict)
INTENT_PARSER = PydanticOutputParser(pydantic_object=IntentDecision)
CONTEXT_PARSER = PydanticOutputParser(pydantic_object=ContextAssessment)

ASSESSOR_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are the Sprints Assessor Agent grading a learner's Python assignment. Use ONLY the execution evidence "
     "supplied; never invent test results. Rubric: {rubric}\n"
     "Feedback points must be specific, cite test counts or error types, and say how to fix the problem.\n"
     "{format_instructions}"),
    ("human",
     "Assignment: {assignment}\n\nSubmission:\n```python\n{code}\n```\n\nExecution evidence (JSON):\n{evidence}\n\n"
     "Issues raised by the judge on the previous attempt (fix them):\n{judge_issues}"),
]).partial(rubric=RUBRIC_TEXT, format_instructions=ASSESSMENT_PARSER.get_format_instructions())

JUDGE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are an independent grading judge. Review the proposed grade against this rubric: {rubric}\n"
     "Approve only if: (1) the score follows the rubric arithmetic from the evidence, (2) pass_status matches the pass mark "
     "(see pass mark in the rubric), (3) every feedback point is supported by the evidence, "
     "(4) failing tests or errors are mentioned, (5) feedback is specific. List concrete issues otherwise.\n{format_instructions}"),
    ("human",
     "Assignment: {assignment}\n\nSubmission:\n```python\n{code}\n```\n\nEvidence (JSON):\n{evidence}\n\nProposed grade (JSON):\n{grade}"),
]).partial(rubric=RUBRIC_TEXT, format_instructions=JUDGE_PARSER.get_format_instructions())

INTENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Classify a Sprints learner message. curriculum_question = asks about course content or policy; "
     "career_match = asks about jobs, placement, partner openings or salary; grade_code = submits Python code or asks for "
     "grading; unknown = none of these.\n{format_instructions}"),
    ("human", "Contains a code block: {has_code}\nMessage: {text}"),
]).partial(format_instructions=INTENT_PARSER.get_format_instructions())

CONTEXT_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Decide whether the retrieved curriculum passages contain enough information to answer the question. "
     "Be strict: sufficient=false if the answer would require facts not present.\n{format_instructions}"),
    ("human", "Question: {question}\nSearch query used: {search_query}\n\nPassages:\n{context}"),
]).partial(format_instructions=CONTEXT_PARSER.get_format_instructions())

REFORMULATE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Rewrite the learner's question as a short search query that uses Sprints curriculum vocabulary "
     "(e.g. MemorySaver, thread ID, interrupt, StateGraph, ChromaDB, chunk overlap). Avoid words already tried. "
     "Reply with the query only."),
    ("human", "Question: {question}\nQueries already tried: {tried}"),
])

ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are the Sprints Advisor Agent. Answer ONLY from the passages below, in at most 5 sentences. If they do not "
     "contain the answer, say you could not find it in the curriculum. End with 'Sources: <file names>'."),
    ("human", "Question: {question}\n\nPassages:\n{context}"),
])
