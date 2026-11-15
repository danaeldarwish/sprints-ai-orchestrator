# Module 4: LangGraph State Graphs and Multi-Agent Orchestration

> Synthetic Sprints curriculum content created for this project.

## StateGraph and state
LangGraph models an application as a graph of nodes that read and update a shared state. Define the state as a `TypedDict`. Fields with a reducer, such as the messages list with `add_messages`, accumulate updates; other fields are overwritten.

## Nodes and edges
A node is a function that receives the state and returns a partial update. Normal edges always go to the same next node. Conditional edges call a routing function that inspects the state and returns the name of the next node. Conditional edges are how loops and branches are expressed.

## Orchestrator-worker pattern
An orchestrator node classifies each incoming learner message by intent and routes it to a specialist worker. In Sprints the Advisor Agent handles curriculum questions and career matching, and the Assessor Agent grades Python code. Routing in a graph replaces linear chains, which cannot branch.

## Evaluator-optimizer pattern
A generator produces a result and an evaluator, often a second model acting as a judge, checks it against an explicit rubric. If the judge finds problems, the generator tries again with the judge's issues as extra input. Always cap the loop: the Assessor Agent stops after a maximum of 3 refinement iterations to control cost and latency, and flags the result for human review if the judge is still unhappy.

## Message protocol
Workers and the orchestrator exchange HumanMessage, AIMessage and ToolMessage objects. Logging each message with its node name gives a full audit trail of who said what and which tool returned which data.

## Graceful degradation
When a tool fails, the node should return a structured "Unable to verify" result and let the graph finish cleanly rather than raising an exception to the learner.
