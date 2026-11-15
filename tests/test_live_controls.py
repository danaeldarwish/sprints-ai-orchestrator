"""Offline HTTP fixtures verify the live budget without contacting a provider."""
import json
import httpx
import pytest
from langchain_core.messages import HumanMessage
from src.live_controls import RequestBudget,ControlledChatOpenAI,LiveRunStopped,MODEL

def model(budget,handler):
    return ControlledChatOpenAI(budget=budget,api_key='offline-test-sentinel',model=MODEL,max_tokens=500,n=1,max_retries=0,timeout=20,streaming=False,cache=False,use_responses_api=False,include_response_headers=True,http_client=httpx.Client(transport=httpx.MockTransport(handler),trust_env=False,follow_redirects=False))
def good(request):
    return httpx.Response(200,headers={'x-request-id':'fixture-request'},json={'id':'fixture-response','model':MODEL,'object':'chat.completion','created':0,'choices':[{'index':0,'message':{'role':'assistant','content':'ok'},'finish_reason':'stop'}],'usage':{'prompt_tokens':50,'completion_tokens':1,'total_tokens':51}})
def test_shared_budget_counts_two_model_instances_and_bound_tools():
    hits=[]
    def handler(req):hits.append(req);return good(req)
    budget=RequestBudget(2);a=model(budget,handler);b=model(budget,handler)
    a.invoke('one');b.bind_tools([{'type':'function','function':{'name':'get_learner_profile','parameters':{'type':'object','properties':{}}}}]).invoke('two')
    with pytest.raises(LiveRunStopped):a.invoke('three')
    assert len(hits)==2 and len(budget.records)==2
    assert budget.records[0]['request_id']=='fixture-request'
    assert budget.records[0]['token_usage']['total_tokens']==51
    journal=json.dumps(budget.records)
    assert 'offline-test-sentinel' not in journal and 'Authorization' not in journal

def test_http_failure_is_counted_and_stops_later_requests():
    hits=[]
    def handler(req):hits.append(req);return httpx.Response(429,json={'error':{'message':'fixture limit','type':'rate_limit','code':'rate_limit'}})
    budget=RequestBudget();a=model(budget,handler)
    with pytest.raises(Exception):a.invoke('one')
    with pytest.raises(LiveRunStopped):a.invoke('two')
    assert len(hits)==1 and len(budget.records)==1 and budget.stopped
    assert budget.records[0]['http_status']==429

@pytest.mark.parametrize('kwargs',[{'max_tokens':501},{'max_completion_tokens':501},{'n':2},{'model':'unapproved-model'},{'timeout':120},{'extra_body':{'max_tokens':9999}}])
def test_bound_output_overrides_cannot_expand_envelope(kwargs):
    hits=[];a=model(RequestBudget(),lambda req:hits.append(req) or good(req))
    with pytest.raises(LiveRunStopped):a.bind(**kwargs).invoke('one')
    assert not hits

def test_oversize_input_rejected_before_http():
    hits=[];budget=RequestBudget();a=model(budget,lambda req:hits.append(req) or good(req))
    with pytest.raises(LiveRunStopped):a.invoke('long text '*5000)
    assert not hits and not budget.records and budget.stopped

def test_stream_cannot_bypass_budget():
    hits=[];a=model(RequestBudget(),lambda req:hits.append(req) or good(req))
    with pytest.raises(LiveRunStopped):list(a.stream('one'))
    assert not hits

def test_repair_retry_consumes_shared_budget():
    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.exceptions import OutputParserException
    hits=[];budget=RequestBudget(2);a=model(budget,lambda req:hits.append(req) or good(req))
    chain=(a|JsonOutputParser()).with_retry(retry_if_exception_type=(OutputParserException,),stop_after_attempt=2,wait_exponential_jitter=False)
    with pytest.raises(OutputParserException):chain.invoke('one')
    assert len(hits)==2 and len(budget.records)==2

def test_factory_does_not_read_ambient_openai_key(monkeypatch):
    import src.live_controls as live
    monkeypatch.setattr(live.config,'LIVE_CALLS_AUTHORIZED',True)
    monkeypatch.setattr(live.config,'OPENAI_CHAT_MODEL',MODEL)
    monkeypatch.delenv('SPRINTS_VERIFICATION_API_KEY',raising=False)
    monkeypatch.setenv('OPENAI_API_KEY','unrelated-offline-sentinel')
    with pytest.raises(PermissionError,match='Dedicated'):live.make_controlled_model()


def test_hosted_tools_cannot_add_provider_spend():
    hits=[];a=model(RequestBudget(),lambda req:hits.append(req) or good(req))
    with pytest.raises(LiveRunStopped):a.bind(tools=[{'type':'web_search'}]).invoke('one')
    assert not hits
