# Project charter - Sprints AI Orchestrator

Sprints Student Success needs a unified workflow for curriculum questions, Python assessment and career advice. The discovery working notes specify typed LangGraph orchestration, per-learner checkpoints, securely sandboxed grading, grounded employer matching and a live demonstration.

The business target is an 80% reduction in student waiting time. No measured baseline or achieved reduction is available. The available dataset has 25 learners; curriculum and opening records are synthetic stand-ins.

Scope includes the existing Advisor/Assessor graph, exact-token ingestion, Pydantic feedback, scoped SQL tools, bounded RAG reflection, evaluator-optimizer, trusted mock sessions, authorized human review and graduation deliverables. Production identity, durable state, real openings and deployment remain next steps.

The project rubric totals 100 points with a pass score of 60. This differs from the learner assessment pass assumption of 70. Named sponsors and staffing commitments in the original charter are unverified because original kickoff/audio media are absent.

Priority release gates: verify real isolated execution, verify paid OpenAI inference only after authorization, record the actual 3-5 minute demonstration, and address cold retrieval threshold failures. Reference provenance is recorded in _client_sources/README.md.
