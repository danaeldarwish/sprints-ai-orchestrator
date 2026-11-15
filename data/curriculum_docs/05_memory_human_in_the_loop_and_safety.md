# Module 5: Memory, Human-in-the-Loop and Safety

> Synthetic Sprints curriculum content created for this project.

## Conversation memory with checkpointers
A checkpointer saves the graph state after every step. With `MemorySaver`, each conversation is stored under a thread ID passed in the run configuration. The trusted application allocates an opaque thread ID for each authenticated mock learner. A thread ID is not authentication: the application must verify ownership before every checkpoint read, write or resume. Context persists across turns through MemorySaver. `MemorySaver` keeps data in process memory; production systems use a database-backed checkpointer such as SQLite or Postgres so state survives restarts.

## Human-in-the-loop with interrupt
Some decisions are too important to automate. Calling `interrupt()` inside a node pauses the graph and surfaces a payload to a human reviewer. The graph resumes when the application invokes it again with a `Command(resume=...)` value on the same thread ID. Because the node restarts from its beginning on resume, avoid side effects before the interrupt call. Interrupts require a checkpointer.

## When Sprints requires human approval
A placement recommendation that includes a tier-1 partner, currently Fawry, must be approved by a Sprints career advisor before the learner sees it. An application-issued reviewer session with scope for this learner must explicitly approve or reject, with a required rationale. Strict Pydantic validation binds the one-time decision to the pending action. Rejection withholds the draft and replay is denied. Placements for other partners are released automatically once they pass the data checks.

## Sandboxing learner code
Never run learner code with plain `exec` or an unrestricted REPL. The Sprints POC requires a restricted Linux container with no network, non-root execution, a read-only root filesystem, no host mounts, CPU and memory limits, a process cap, bounded output and a wall-clock timeout. Static screening and restricted builtins add defense in depth. If containment cannot be established, return Unable to verify and execute nothing on the host.

## Preventing hallucinations in career matching
An agent must never invent qualifications, salaries or employers. Career messages are built only from database rows, and a grounding check verifies that every partner name, opening ID and EGP amount in the message appears in the retrieved records. If a record is missing the correct answer is "Unable to verify".

## Privacy
A learner may only access their own record. Requests about another learner's data are refused.
