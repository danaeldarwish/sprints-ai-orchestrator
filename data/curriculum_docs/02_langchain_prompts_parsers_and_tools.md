# Module 2: LangChain Prompts, Output Parsers and Tools

> Synthetic Sprints curriculum content created for this project.

## Prompt templates
A `ChatPromptTemplate` turns variables into a list of system and human messages. Keep instructions in the system message and the data in the human message. Typed placeholders such as `{question}` make prompts testable and reusable.

## Structured output with Pydantic
Free-text model answers are hard to automate. Define a Pydantic model with typed fields and constraints, for example a score between 0 and 100, then use a `PydanticOutputParser` to inject format instructions into the prompt and to validate the reply. If the model returns malformed JSON, the parser raises an error that you can catch and retry. Strict schemas are how the Assessor Agent returns a score, a list of feedback points and a pass status in a predictable shape.

## Chains with LCEL
The pipe operator composes steps: `prompt | model | parser`. Chains are ideal for fixed, linear work such as one grading call. They are not the right tool for dynamic routing between agents, which belongs in LangGraph.

## Tools
A tool is a Python function with a name, a typed signature and a docstring that the model reads to decide when to call it. Decorate a function with `@tool`. Good tool descriptions state inputs, outputs and failure behaviour. Tools must never crash the agent: catch exceptions and return a structured error message instead.

## ReAct agents
ReAct alternates between reasoning and acting. The model emits an AI message containing a tool call, the tool node runs it and returns a ToolMessage, and the loop repeats until the model answers without a tool call. The three message types, HumanMessage, AIMessage and ToolMessage, make every step traceable in logs.

## SQL tools
A SQL tool lets an agent look up facts that must be exact, such as a learner's completed modules, target salary in EGP and preferred employers. Open the database read-only, accept only a single SELECT statement, and never let the model invent values: answers about a learner must come from the returned rows.
