"""
Inspect AI trace format adapter.

Converts Inspect AI evaluation trace (input, target, messages, metadata)
to ReCoMo ReasoningTrace for plug-and-play use in their ecosystem.
"""

import hashlib
import json
from typing import Any, Dict, List

from recomo.trace_schema import ReasoningTrace, Turn


def inspect_trace_to_reasoning_trace(
    inspect_trace: Dict[str, Any],
    *,
    trace_id: str | None = None,
    agent_name: str = "agent",
) -> ReasoningTrace:
    """
    Convert an Inspect AI trace to ReasoningTrace.

    Inspect AI format (simplified):
      - input: task prompt
      - target: expected output (optional)
      - messages: [{"role": "system"|"user"|"assistant", "content": "..."}, ...]
      - metadata: optional dict

    We map: input -> task, messages -> turns (with turn_number 1-based),
    trace_id from metadata or hash of input+messages.
    """
    task = inspect_trace.get("input") or ""
    messages = inspect_trace.get("messages") or []
    metadata = inspect_trace.get("metadata") or {}

    if trace_id is None:
        trace_id = metadata.get("trace_id") or metadata.get("id")
    if trace_id is None:
        payload = json.dumps({"input": task, "messages": messages}, sort_keys=True)
        trace_id = hashlib.sha256(payload.encode()).hexdigest()[:16]

    turns: List[Turn] = []
    for i, msg in enumerate(messages):
        role = (msg.get("role") or "assistant").lower()
        if role == "assistant":
            role = "agent"
        content = msg.get("content") or ""
        if isinstance(content, list):
            # Some formats use [{"type":"text","text":"..."}]
            parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
            content = " ".join(parts) if parts else str(content)
        turns.append(Turn(turn_number=i + 1, role=role, content=content, metadata=None))

    return ReasoningTrace(
        trace_id=trace_id,
        agent_name=agent_name,
        task=task,
        turns=turns,
    )
