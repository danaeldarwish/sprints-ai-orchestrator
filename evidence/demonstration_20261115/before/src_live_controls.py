"""Controlled Sprints inference: one shared budget across reasoner and SQL ReAct.

Preparation is offline. Only the separately authorized CLI may supply a dedicated
verification key. No dotenv loading, ambient OPENAI_API_KEY, embeddings, streaming,
SDK retry or provider/model substitution is part of this envelope.
"""
from __future__ import annotations
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime,timezone
import hashlib,json,os,threading,time
import httpx
from langchain_core.messages import messages_to_dict
from langchain_openai import ChatOpenAI
from pydantic import PrivateAttr
from src import config
from src.tokens import count_tokens
MODEL='gpt-4o-mini-2024-07-18'
MAX_REQUESTS=24
MAX_INPUT_TOKENS=4000
MAX_OUTPUT_TOKENS=500
CASE=ContextVar('sprints_live_case',default='unspecified')
class LiveRunStopped(RuntimeError):
    """The approved request envelope is exhausted or a provider attempt failed."""
class RequestBudget:
    """Serialize and count outbound attempts, including repair attempts and errors.

    JSON message/tool token count plus 1024 tokens is a conservative local
    admission estimate; server usage is authoritative. No raw prompts are logged.
    """
    def __init__(self,max_requests=MAX_REQUESTS):
        if not 1<=max_requests<=MAX_REQUESTS:raise ValueError('Invalid request ceiling')
        self.max_requests=max_requests;self.records=[];self.stopped=False;self._lock=threading.RLock()
    @contextmanager
    def attempt(self,messages,kwargs,model):
        with self._lock:
            if self.stopped or len(self.records)>=self.max_requests:raise LiveRunStopped('Run stopped or request budget exhausted')
            if model!=MODEL:raise LiveRunStopped('Model substitution is forbidden')
            if set(kwargs)-{'tools','tool_choice','parallel_tool_calls','n','max_tokens','max_completion_tokens'}:raise LiveRunStopped('Unapproved request option')
            if any(t.get('type')!='function' or t.get('function',{}).get('name') not in {'get_learner_profile','list_matching_openings'} for t in kwargs.get('tools',[])):raise LiveRunStopped('Only the two scoped SQLite function tools are allowed')
            if any(not isinstance(m.content,str) for m in messages):raise LiveRunStopped('Text-only verification required')
            if kwargs.get('n',1)!=1 or kwargs.get('max_tokens',500)>500 or kwargs.get('max_completion_tokens',500)>500:raise LiveRunStopped('Output envelope exceeded')
            payload=json.dumps({'messages':messages_to_dict(messages),'options':kwargs},sort_keys=True,default=str,ensure_ascii=False)
            estimate=count_tokens(payload)+1024
            if estimate>MAX_INPUT_TOKENS:self.stopped=True;raise LiveRunStopped('Conservative input-token ceiling exceeded')
            row={'attempt':len(self.records)+1,'case':CASE.get(),'at':datetime.now(timezone.utc).isoformat(),'model':model,'local_input_admission_tokens':estimate,'prompt_sha256':hashlib.sha256(payload.encode()).hexdigest()}
            self.records.append(row);start=time.perf_counter()
            try:yield row
            except Exception as exc:
                self.stopped=True;row.update(status='stopped',exception=type(exc).__name__,http_status=getattr(exc,'status_code',None));raise
            finally:row['latency_ms']=round((time.perf_counter()-start)*1000,3)
    def assert_active(self):
        if self.stopped or len(self.records)>=self.max_requests:raise LiveRunStopped('Run stopped or request budget exhausted')
_SHARED=RequestBudget()
def shared_budget():return _SHARED
def configure_run(budget):
    global _SHARED
    _SHARED=budget
class ControlledChatOpenAI(ChatOpenAI):
    """Synchronous Chat Completions adapter with hard shared attempt admission."""
    _sprints_budget:RequestBudget=PrivateAttr()
    def __init__(self,*,budget,**kwargs):
        super().__init__(**kwargs);self._sprints_budget=budget
    def _generate(self,messages,stop=None,run_manager=None,**kwargs):
        if self.streaming:raise LiveRunStopped('Streaming is outside this verification envelope')
        options={'n':self.n,'max_tokens':self.max_tokens,**self.model_kwargs,**kwargs}
        with self._sprints_budget.attempt(messages,options,self.model_name) as row:
            result=super()._generate(messages,stop=stop,run_manager=run_manager,**kwargs)
            meta=result.llm_output or {};first=result.generations[0]
            row.update(status='received',response_id=meta.get('id'),returned_model=meta.get('model_name'),token_usage=meta.get('token_usage'),finish_reason=(first.generation_info or {}).get('finish_reason'),request_id=(first.generation_info or {}).get('headers',{}).get('x-request-id'))
            usage=meta.get('token_usage') or {}
            if usage.get('prompt_tokens',0)>MAX_INPUT_TOKENS or usage.get('completion_tokens',0)>MAX_OUTPUT_TOKENS:self._sprints_budget.stopped=True;raise LiveRunStopped('Server usage exceeded planned envelope; stop immediately')
            return result
    def stream(self,*args,**kwargs):raise LiveRunStopped('Streaming verification is disabled')
    async def astream(self,*args,**kwargs):
        raise LiveRunStopped('Streaming verification is disabled')
        yield
    async def _agenerate(self,*args,**kwargs):raise LiveRunStopped('Async verification is disabled')
    def _stream(self,*args,**kwargs):raise LiveRunStopped('Streaming verification is disabled')
    async def _astream(self,*args,**kwargs):
        raise LiveRunStopped('Streaming verification is disabled')
        yield

def make_controlled_model():
    """Read only the explicitly provisioned verification credential after approval."""
    if not config.LIVE_CALLS_AUTHORIZED:raise PermissionError('Separate explicit paid-call approval required')
    if config.OPENAI_CHAT_MODEL!=MODEL:raise PermissionError('Set the exact approved model; no substitution')
    key=os.environ.get('SPRINTS_VERIFICATION_API_KEY')
    if not key:raise PermissionError('Dedicated SPRINTS_VERIFICATION_API_KEY must be provisioned by the user')
    return ControlledChatOpenAI(budget=shared_budget(),model=MODEL,api_key=key,base_url='https://api.openai.com/v1',temperature=0,timeout=20,max_retries=0,max_tokens=500,n=1,streaming=False,cache=False,use_responses_api=False,include_response_headers=True,http_client=httpx.Client(trust_env=False,follow_redirects=False,timeout=20))
