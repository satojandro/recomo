"""
Simulation runner: load a scenario and run agent (LLM) to produce a ReasoningTrace.

Uses the same LLM client as the rest of ReCoMo (OpenRouter via get_llm_client_and_model).
"""

import json
import sys
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
    print_live: bool = False,
) -> ReasoningTrace:
    """
    Run a scenario: system turn + alternating user messages and agent (LLM) responses.
    Returns a ReasoningTrace with trace_id = scenario.id.
    If client is provided (e.g. for tests), it must have chat.completions.create(model, messages).
    If print_live is True, print each turn and show a progress bar (no-op when client is provided).
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
    use_progress = print_live
    if use_progress:
        try:
            from tqdm import tqdm
        except ImportError:
            use_progress = False

    def _print_turn(role: str, content: str, turn_num: int, max_chars: int = 500) -> None:
        if not print_live:
            return
        text = (content or "").strip()
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        print(f"[Turn {turn_num}] {role.upper()}: {text}")
        print()
        sys.stdout.flush()

    # Turn 1: system
    messages.append({"role": "system", "content": s.system_prompt})
    turns.append(Turn(turn_number=1, role="system", content=s.system_prompt))
    _print_turn("system", s.system_prompt, 1, max_chars=300)

    turn_number = 2
    iterator = s.user_messages
    if use_progress:
        iterator = tqdm(iterator, desc="Scenario", unit="exchange")
    for user_msg in iterator:
        messages.append({"role": "user", "content": user_msg})
        turns.append(Turn(turn_number=turn_number, role="user", content=user_msg))
        _print_turn("user", user_msg, turn_number)
        turn_number += 1

        response = client.chat.completions.create(model=effective_model, messages=messages)
        content = response.choices[0].message.content or ""
        messages.append({"role": "assistant", "content": content})
        turns.append(Turn(turn_number=turn_number, role="agent", content=content))
        _print_turn("agent", content, turn_number)
        turn_number += 1

    return ReasoningTrace(
        trace_id=s.id,
        agent_name=agent_name,
        task=s.task,
        turns=turns,
    )
