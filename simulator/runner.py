"""
Simulation runner: load a scenario and run agent (LLM) to produce a ReasoningTrace.

Uses the same LLM client as the rest of ReCoMo (OpenRouter via get_llm_client_and_model).
"""

import json
from pathlib import Path
from typing import List

from recomo.trace_schema import ReasoningTrace, Turn


def _load_scenario(source: "Scenario | str | Path") -> "Scenario":
    """Load Scenario from path (JSON) or return Scenario as-is."""
    from recomo.demo.scenarios.schema import Scenario

    if isinstance(source, Scenario):
        return source
    path = Path(source) if isinstance(source, str) else source
    if not path.exists():
        raise FileNotFoundError(f"Scenario file not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return Scenario.model_validate(data)


def run_scenario(
    scenario: "Scenario | str | Path",
    *,
    model: str | None = None,
    agent_name: str = "SimulatedAgent",
    client: object | None = None,
) -> ReasoningTrace:
    """
    Run a scenario: system turn + alternating user messages and agent (LLM) responses.
    Returns a ReasoningTrace with trace_id = scenario.id.
    If client is provided (e.g. for tests), it must have chat.completions.create(model, messages).
    """
    from recomo.demo.scenarios.schema import Scenario
    from recomo.extractor.claim_extractor import get_llm_client_and_model

    s = _load_scenario(scenario)
    if client is None:
        client, default_model = get_llm_client_and_model()
        effective_model = model if model is not None else default_model
    else:
        effective_model = model or "test-model"

    messages: List[dict] = []
    turns: List[Turn] = []

    # Turn 1: system
    messages.append({"role": "system", "content": s.system_prompt})
    turns.append(Turn(turn_number=1, role="system", content=s.system_prompt))

    turn_number = 2
    for user_msg in s.user_messages:
        messages.append({"role": "user", "content": user_msg})
        turns.append(Turn(turn_number=turn_number, role="user", content=user_msg))
        turn_number += 1

        response = client.chat.completions.create(model=effective_model, messages=messages)
        content = response.choices[0].message.content or ""
        messages.append({"role": "assistant", "content": content})
        turns.append(Turn(turn_number=turn_number, role="agent", content=content))
        turn_number += 1

    return ReasoningTrace(
        trace_id=s.id,
        agent_name=agent_name,
        task=s.task,
        turns=turns,
    )
