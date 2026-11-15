"""Agentic message protocol helpers + verbose trace logging (Sprint 2).

Orchestrator and workers communicate only through HumanMessage, AIMessage and
ToolMessage objects. ``tool_exchange`` records a tool call as the standard
AIMessage(tool_calls) -> ToolMessage pair, and ``traced`` logs every node's
messages on the ``sprints.trace`` logger so a run can be audited end to end.
"""
from __future__ import annotations

import functools
import logging
import uuid
from typing import Callable

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

trace_log = logging.getLogger("sprints.trace")


def tool_exchange(agent: str, tool_name: str, args: dict, result: str) -> list[BaseMessage]:
    """Return the AIMessage(tool call) + ToolMessage(result) pair for one tool invocation."""
    call_id = f"call_{uuid.uuid4().hex[:8]}"
    return [
        AIMessage(content="", name=agent, tool_calls=[{"name": tool_name, "args": args, "id": call_id, "type": "tool_call"}]),
        ToolMessage(content=result, name=tool_name, tool_call_id=call_id),
    ]


def describe(msg: BaseMessage, width: int = 150) -> str:
    """One-line description of a message for the trace log."""
    kind = type(msg).__name__
    if getattr(msg, "tool_calls", None):
        calls = ", ".join(c['name'] for c in msg.tool_calls)
        return f"{kind}[{msg.name or 'agent'}] tool_call: {calls}"
    who = getattr(msg, "name", None)
    return f"{kind}{f'[{who}]' if who else ''}: content omitted from metadata trace"


def traced(node: str) -> Callable:
    """Decorator: log node entry and every message the node emits."""

    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(state, *args, **kwargs):
            trace_log.info("▶ node=%s", node)
            update = fn(state, *args, **kwargs)
            for m in (update or {}).get("messages", []):
                trace_log.info("   [%s] %s", node, describe(m))
            return update

        return wrapper

    return deco
