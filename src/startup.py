"""Sprints startup gate: prepare actual Chroma before exposing a learner service.

The default CLI uses this gate. The trusted warm=False service option remains
an explicit fixture/benchmark override and must not be used by a serving host.
"""
from dataclasses import dataclass,field
from time import perf_counter
from src.tools.rag_retriever import warm_up
from src.service import OrchestratorService
@dataclass(frozen=True)
class ApplicationStartup:
    status:str
    duration_ms:float
    message:str
    service:object=field(default=None,repr=False,compare=False)
    error_type:str|None=None
    def to_dict(self):
        return {'status':self.status,'accepting_learner_requests':self.status=='READY','startup_ms':self.duration_ms,'message':self.message,'error_type':self.error_type}
def prepare_application(identities,**graph_options):
    """Initialize vector store, collection and a real query before graph exposure.

    A successful query prepares the persisted index through Chroma's query API;
    no private index-loading implementation or latency guarantee is assumed.
    Failure exposes no partially constructed service. Startup is measured apart
    from the 1000 ms prepared retrieval budget, including all slow cold work.
    """
    if 'warm' in graph_options:raise ValueError('Serving startup cannot bypass curriculum readiness')
    began=perf_counter()
    try:
        warm_up()
        app=OrchestratorService(identities,warm=False,**graph_options)
    except Exception as exc:
        return ApplicationStartup('UNAVAILABLE',round((perf_counter()-began)*1000,3),'Application initialization failed; learner requests are not accepted.',error_type=type(exc).__name__)
    return ApplicationStartup('READY',round((perf_counter()-began)*1000,3),'Curriculum collection and preparation query succeeded.',service=app)
