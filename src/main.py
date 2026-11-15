"""Sprints POC CLI. Default offline demo leaves every tier-1 review pending.

Mock session issuance is trusted local application bootstrap, not real login.
No auto-approval switch exists. A real terminal operator may use review-demo.
"""
from __future__ import annotations
import argparse
import json
import logging
import sys
from src.auth import MockIdentityProvider
from src.startup import prepare_application
from src.tools.code_repl import sandbox_capabilities

BUGGY = '''Please grade my clean_scores assignment:
```python
def clean_scores(scores):
    return round(sum(s for s in scores if s) / len(scores), 2)
```'''
FIXED = '''Please grade my clean_scores assignment:
```python
def clean_scores(scores):
    """Return the mean of valid scores, or zero when none remain."""
    valid = [s for s in scores if s is not None and s >= 0]
    return round(sum(valid) / len(valid), 2) if valid else 0.0
```'''

def ready_service(ids):
    """Print explicit readiness; unavailable startup exits before learner input."""
    startup=prepare_application(ids)
    print(json.dumps(startup.to_dict(),indent=2))
    if startup.status!='READY':raise SystemExit(2)
    return startup.service

def run_demo() -> list[dict]:
    """Use real LangGraph, Chroma and SQLite with offline heuristic reasoning."""
    ids = MockIdentityProvider()
    app = ready_service(ids)
    sessions = {n: ids.issue_mock_session(f"learner-{n}") for n in (1001,1003,1005,1013)}
    scenes = [
        ("curriculum",1001,"How do I make my agent remember each student across sessions?"),
        ("buggy_code",1005,BUGGY),("corrected_code",1005,FIXED),
        ("database_career",1003,"Which partner openings match me?"),
        ("tier1_pending",1013,"Which partner openings match me?"),
        ("other_learner_denied",1003,"What salary does SPR-1001 want?"),
    ]
    results = []
    print("OFFLINE DEMO: heuristic reasoner and scripted ReAct; no OpenAI inference.")
    print("Python results require a verified Linux sandbox. Tier-1 stays pending.")
    for name, n, text in scenes:
        print(f"\nSCENARIO {name}")
        result = app.ask(sessions[n], {"text":text})
        print(json.dumps(result, indent=2, ensure_ascii=True))
        results.append({"scenario":name,**result})
    return results

def review_demo():
    """Explicit terminal review with a scoped, application-issued mock reviewer."""
    if not sys.stdin.isatty():
        raise SystemExit("Interactive authorized human review requires a terminal; nothing was approved.")
    ids = MockIdentityProvider()
    app = ready_service(ids)
    learner = ids.issue_mock_session("learner-1013")
    reviewer = ids.issue_mock_session("career-reviewer")
    pending = app.ask(learner, {"text":"Which partner openings match me?"})
    print(json.dumps(pending, indent=2))
    draft = app.pending_review(reviewer, pending["pending_id"])
    print(draft["draft"])
    choice = input("Authorized mock reviewer: type APPROVE or REJECT explicitly: ").strip()
    if choice not in {"APPROVE","REJECT"}:
        print("No valid explicit decision; recommendation remains pending.")
        return
    note = input("Review rationale (required): ").strip()
    if not note:
        print("Missing rationale; recommendation remains pending.")
        return
    result = app.review(reviewer, {"pending_id":pending["pending_id"],"approved":choice=="APPROVE","note":note})
    print(json.dumps(result,indent=2))
    print(json.dumps(app.audit_events(reviewer),indent=2))

def run_chat(account):
    ids=MockIdentityProvider()
    token=ids.issue_mock_session(account)
    app=ready_service(ids)
    print("Local mock-authenticated learner session. Tier-1 reviews stay pending.")
    while True:
        try: text=input("you> ")
        except (EOFError,KeyboardInterrupt): break
        try: print(json.dumps(app.ask(token,{"text":text}),indent=2))
        except PermissionError as exc: print(str(exc))

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=["demo","chat","ingest","build-db","sandbox-status","review-demo","readiness"])
    parser.add_argument("--mock-account",choices=[f"learner-{n}" for n in range(1001,1026)],default="learner-1001")
    parser.add_argument("--verbose",action="store_true",help="metadata-only protocol trace; no records or tokens")
    args=parser.parse_args(argv)
    if args.verbose:
        logging.basicConfig(level=logging.INFO,format="%(name)s %(message)s",stream=sys.stdout)
    if args.command=="demo": run_demo()
    elif args.command=="review-demo": review_demo()
    elif args.command=="chat": run_chat(args.mock_account)
    elif args.command=="readiness": ready_service(MockIdentityProvider())
    elif args.command=="sandbox-status": print(json.dumps(sandbox_capabilities(),indent=2))
    elif args.command=="build-db":
        from src.tools.db_queries import build_database
        print(json.dumps(build_database(),indent=2))
    else:
        from dataclasses import asdict
        from src.tools.rag_retriever import ingest_curriculum
        print(json.dumps(asdict(ingest_curriculum()),indent=2))
if __name__=="__main__": main()
