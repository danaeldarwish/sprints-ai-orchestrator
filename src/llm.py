"""Model backends: the OpenAI-backed ``LLMReasoner`` and the offline ReAct model.

``get_reasoner()`` returns the backend selected by ``SPRINTS_LLM`` (offline | openai).
Both implement the same interface, so graph code never depends on a provider.
Curriculum mapping: Module 2 (chains = prompt | model | parser).
"""
from __future__ import annotations

import json
import re
from typing import Any, Protocol

from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from src import config, prompts
from src.heuristics import HeuristicReasoner
from src.schemas import AssessmentResult, ContextAssessment, IntentDecision, JudgeVerdict


class Reasoner(Protocol):
    """Language judgements the graph needs. Implemented by HeuristicReasoner and LLMReasoner."""

    name: str

    def classify_intent(self, text: str, has_code: bool) -> IntentDecision: ...
    def assess_context(self, question: str, search_query: str, chunks: list[dict]) -> ContextAssessment: ...
    def reformulate(self, question: str, tried: list[str]) -> str: ...
    def compose_answer(self, question: str, search_query: str, chunks: list[dict], sufficient: bool) -> str: ...
    def grade(self, assignment: dict, code: str, evidence: dict, judge_issues: list[str], refinement: int) -> AssessmentResult: ...
    def judge(self, assignment: dict, code: str, evidence: dict, result: AssessmentResult) -> JudgeVerdict: ...


def _ctx(chunks: list[dict]) -> str:
    return "\n\n".join(f"[{c['source']}]\n{c['text']}" for c in chunks[:3])


class LLMReasoner:
    """Reasoner backed by any LangChain chat model using ``prompt | llm | PydanticOutputParser`` chains."""

    def __init__(self, llm: BaseChatModel | None = None) -> None:
        if llm is None:
            from src.live_controls import make_controlled_model

            if not config.LIVE_CALLS_AUTHORIZED:
                raise PermissionError("Paid API use requires explicit authorization and SPRINTS_LIVE_AUTHORIZED=1")
            llm = make_controlled_model()
        self.llm = llm
        self.name = f"llm:{getattr(llm, 'model_name', type(llm).__name__)}"
        retry = dict(retry_if_exception_type=(OutputParserException,), stop_after_attempt=2)
        self._intent = (prompts.INTENT_PROMPT | llm | prompts.INTENT_PARSER).with_retry(**retry)
        self._context = (prompts.CONTEXT_PROMPT | llm | prompts.CONTEXT_PARSER).with_retry(**retry)
        self._grade = (prompts.ASSESSOR_PROMPT | llm | prompts.ASSESSMENT_PARSER).with_retry(**retry)
        self._judge = (prompts.JUDGE_PROMPT | llm | prompts.JUDGE_PARSER).with_retry(**retry)
        self._reform = prompts.REFORMULATE_PROMPT | llm | StrOutputParser()
        self._answer = prompts.ANSWER_PROMPT | llm | StrOutputParser()

    def classify_intent(self, text: str, has_code: bool) -> IntentDecision:
        return self._intent.invoke({"text": text, "has_code": has_code})

    def assess_context(self, question: str, search_query: str, chunks: list[dict]) -> ContextAssessment:
        return self._context.invoke({"question": question, "search_query": search_query, "context": _ctx(chunks)})

    def reformulate(self, question: str, tried: list[str]) -> str:
        return self._reform.invoke({"question": question, "tried": "; ".join(tried)}).strip()

    def compose_answer(self, question: str, search_query: str, chunks: list[dict], sufficient: bool) -> str:
        if not sufficient or not chunks:
            return "I could not find that in the Sprints curriculum, so I won't guess."
        return self._answer.invoke({"question": question, "context": _ctx(chunks)}).strip()

    def grade(self, assignment: dict, code: str, evidence: dict, judge_issues: list[str], refinement: int) -> AssessmentResult:
        return self._grade.invoke({
            "assignment": assignment["prompt"], "code": code, "evidence": json.dumps(evidence)[:6000],
            "judge_issues": "\n".join(judge_issues) or "none (first attempt)"})

    def judge(self, assignment: dict, code: str, evidence: dict, result: AssessmentResult) -> JudgeVerdict:
        return self._judge.invoke({
            "assignment": assignment["prompt"], "code": code, "evidence": json.dumps(evidence)[:6000],
            "grade": result.model_dump_json()})


class ScriptedChatModel(BaseChatModel):
    """Offline chat model that drives the ReAct loop with real tool-call messages.

    Emits ``AIMessage(tool_calls=...)`` for each tool in ``tool_plan`` (reading the learner id from the last
    HumanMessage), stops early if a tool reports ``unable_to_verify``, then emits a final AIMessage. Lets the
    ReAct graph, ToolNode and message protocol run unchanged without an API key.
    """

    tool_plan: list[str] = Field(default_factory=lambda: ["get_learner_profile", "list_matching_openings"])

    @property
    def _llm_type(self) -> str:
        return "sprints-scripted-react"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ScriptedChatModel":
        return self

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs: Any) -> ChatResult:
        last_h = max((i for i, m in enumerate(messages) if isinstance(m, HumanMessage)), default=-1)
        text = str(messages[last_h].content) if last_h >= 0 else ""
        lid = (re.search(r"SPR-\d+", text, re.I) or [""])[0]
        tool_msgs = [m for m in messages[last_h + 1:] if isinstance(m, ToolMessage)]
        failed = any("unable_to_verify" in str(m.content) for m in tool_msgs)
        if len(tool_msgs) < len(self.tool_plan) and not failed:
            msg = AIMessage(content="", tool_calls=[{"name": self.tool_plan[len(tool_msgs)], "args": {"learner_id": lid},
                                                      "id": f"call_{len(tool_msgs) + 1}", "type": "tool_call"}])
        else:
            msg = AIMessage(content=f"Lookup finished for {lid or 'the learner'}"
                                    f"{' with errors' if failed else ''}; see tool results.")
        return ChatResult(generations=[ChatGeneration(message=msg)])


def get_reasoner() -> Reasoner:
    """Reasoner selected by ``SPRINTS_LLM``."""
    return LLMReasoner() if config.LLM_PROVIDER == "openai" else HeuristicReasoner()


def get_react_model() -> BaseChatModel:
    """Tool-calling chat model for the Advisor's ReAct SQL agent."""
    if config.LLM_PROVIDER == "openai":
        from src.live_controls import make_controlled_model

        if not config.LIVE_CALLS_AUTHORIZED:
            raise PermissionError("Paid API use requires explicit authorization and SPRINTS_LIVE_AUTHORIZED=1")
        return make_controlled_model()
    return ScriptedChatModel()
