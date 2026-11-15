"""Focused offline readiness, supported-model and cost preflight regressions."""
import json,threading
from datetime import datetime,timezone,timedelta
import pytest
from langchain_core.messages import HumanMessage
from src import startup
from src.live_controls import RequestBudget,LiveRunStopped,ATTEMPT_RESERVATION_USD,MODEL
from src.preflight import validate_preflight
from tests.test_live_controls import model,good

def test_startup_never_exposes_service_before_preparation(monkeypatch):
    entered=threading.Event();release=threading.Event();created=[];result=[]
    def prepare():entered.set();assert release.wait(3);return 12
    monkeypatch.setattr(startup,'warm_up',prepare)
    monkeypatch.setattr(startup,'OrchestratorService',lambda *a,**k:created.append(k) or object())
    worker=threading.Thread(target=lambda:result.append(startup.prepare_application(object())))
    worker.start();assert entered.wait(2)
    assert not created and not result
    release.set();worker.join(3)
    assert result[0].status=='READY' and result[0].service is not None
    assert created==[{'warm':False}]

def test_startup_failure_has_no_service_and_clear_unavailable_status(monkeypatch):
    def fail():raise OSError('private path omitted')
    monkeypatch.setattr(startup,'warm_up',fail)
    monkeypatch.setattr(startup,'OrchestratorService',lambda *a,**k:pytest.fail('premature graph exposure'))
    result=startup.prepare_application(object())
    assert result.service is None and result.to_dict()['status']=='UNAVAILABLE'
    assert result.to_dict()['accepting_learner_requests'] is False
    assert 'private path' not in json.dumps(result.to_dict())

def test_serving_gate_rejects_warm_bypass():
    with pytest.raises(ValueError):startup.prepare_application(object(),warm=False)

def test_cli_exits_unavailable_before_demo_requests(monkeypatch,capsys):
    import src.main as cli
    monkeypatch.setattr(cli,'prepare_application',lambda ids:startup.ApplicationStartup('UNAVAILABLE',1,'No learner requests accepted'))
    with pytest.raises(SystemExit) as exc:cli.run_demo()
    assert exc.value.code==2 and 'UNAVAILABLE' in capsys.readouterr().out

def test_estimated_cost_reservations_stop_before_http():
    hits=[];budget=RequestBudget(24,max_estimated_cost_usd=ATTEMPT_RESERVATION_USD*2)
    a=model(budget,lambda req:hits.append(req) or good(req))
    a.invoke('one');a.invoke('two')
    with pytest.raises(LiveRunStopped,match='cost'):a.invoke('three')
    assert len(hits)==2 and budget.stopped and len(budget.records)==2

def test_supported_model_serialized_parameters_remain_chat_completions():
    requests=[]
    a=model(RequestBudget(),lambda req:requests.append(json.loads(req.content)) or good(req))
    a.invoke('test')
    body=requests[0]
    assert body['model']==MODEL=='gpt-6-luna'
    assert body['reasoning_effort']=='none' and body['service_tier']=='default'
    assert body.get('max_completion_tokens',body.get('max_tokens'))==500
    assert a.max_retries==0 and not a.use_responses_api

@pytest.mark.parametrize('override',[{'reasoning_effort':'medium'},{'service_tier':'priority'}])
def test_bound_reasoning_or_pricing_override_is_rejected(override):
    a=model(RequestBudget(),lambda req:pytest.fail('unapproved outbound attempt'))
    with pytest.raises(LiveRunStopped):a.bind(**override).invoke('test')

def valid_preflight():
    return {'model':MODEL,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'model_access_confirmed':True,'project_authorized':True,'billing_and_quota_confirmed':True,'standard_global_pricing_confirmed':True,'input_per_million':0.10,'cache_write_per_million':0.125,'output_per_million':0.50}

def test_project_preflight_requires_current_explicit_attestations(tmp_path):
    path=tmp_path/'preflight.json';data=valid_preflight();path.write_text(json.dumps(data))
    assert validate_preflight(path)['model']==MODEL
    for key,value in [('project_authorized',False),('checked_at_utc',(datetime.now(timezone.utc)-timedelta(days=2)).isoformat()),('input_per_million',10)]:
        changed={**data,key:value};path.write_text(json.dumps(changed))
        with pytest.raises(PermissionError):validate_preflight(path)

def test_template_is_not_execution_authorization():
    from pathlib import Path
    with pytest.raises(PermissionError):validate_preflight(Path(__file__).resolve().parents[1]/'docs/openai_preflight.template.json')
