"""Sprint 1: Pydantic schemas, prompt templates, output parsers, LLM chain wiring."""
import pytest
from langchain_core.exceptions import OutputParserException
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from src import prompts
from src.llm import LLMReasoner
from src.rubric import ASSIGNMENTS


def test_assessment_parser_accepts_valid_json():
    r = prompts.ASSESSMENT_PARSER.parse('{"score": 88, "feedback_points": ["Passed 5/6 tests"], "pass_status": "pass"}')
    assert (r.score, r.pass_status) == (88, "pass")


@pytest.mark.parametrize("bad", [
    '{"score": 188, "feedback_points": ["x"], "pass_status": "pass"}',
    '{"score": 50, "feedback_points": [], "pass_status": "fail"}',
    '{"score": 50, "feedback_points": ["ok"], "pass_status": "maybe"}',
    '{"score": 50}', "not json at all",
])
def test_assessment_parser_rejects_invalid(bad):
    with pytest.raises(OutputParserException):
        prompts.ASSESSMENT_PARSER.parse(bad)


def test_prompts_render_with_format_instructions():
    msgs = prompts.ASSESSOR_PROMPT.invoke({"assignment": "a", "code": "print(1)", "evidence": "{}", "judge_issues": "none"}).to_messages()
    assert "feedback_points" in msgs[0].content and "print(1)" in msgs[1].content


def test_llm_reasoner_chain_round_trip_with_fake_model():
    grade = '{"score": 90, "feedback_points": ["Passed 6/6 tests."], "pass_status": "pass"}'
    llm = GenericFakeChatModel(messages=iter([AIMessage(content=grade)]))
    ev = {"run": {"status": "ok"}, "tests": [], "passed": 6, "total": 6}
    res = LLMReasoner(llm=llm).grade(ASSIGNMENTS["clean_scores"], "code", ev, [], 0)
    assert res.score == 90


def test_llm_reasoner_retries_once_on_malformed_output():
    bad, good = AIMessage(content="oops"), AIMessage(content='{"intent":"grade_code","confidence":0.9,"rationale":"code"}')
    r = LLMReasoner(llm=GenericFakeChatModel(messages=iter([bad, good])))
    assert r.classify_intent("grade", True).intent == "grade_code"
