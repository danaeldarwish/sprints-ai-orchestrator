"""Isolated, offline Sprints fixtures. Never read provider credentials."""
import os
import sys
import tempfile
from pathlib import Path
_TMP = tempfile.mkdtemp(prefix="sprints-tests-")
os.environ["SPRINTS_CHROMA_DIR"] = os.path.join(_TMP,"chroma")
os.environ["SPRINTS_DB_PATH"] = os.path.join(_TMP,"learners.db")
os.environ["SPRINTS_LLM"] = "offline"
os.environ["SPRINTS_EMBEDDINGS"] = "hashing"
os.environ["SPRINTS_LIVE_AUTHORIZED"] = "0"
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from src.auth import MockIdentityProvider
from src.service import OrchestratorService
from src.main import BUGGY, FIXED as GOOD
from src.tools.db_queries import build_database
from src.tools.code_repl import sandbox_capabilities

@pytest.fixture(scope="session",autouse=True)
def database():
    return build_database()

@pytest.fixture
def identity():
    return MockIdentityProvider()

@pytest.fixture
def app(identity):
    return OrchestratorService(identity, warm=False)

@pytest.fixture
def ask(app,identity):
    tokens={}
    def call(learner,text,**extra):
        if learner not in tokens:
            tokens[learner]=identity.issue_mock_session("learner-"+learner.removeprefix("SPR-"))
        return app.ask(tokens[learner],{"text":text,**extra})
    call.tokens=tokens
    return call

@pytest.fixture(scope="session")
def capability():
    return sandbox_capabilities()

@pytest.fixture
def container(capability):
    if not capability["available"]:
        pytest.skip("Actual Linux sandbox unavailable: "+capability["reason"])
    return capability
