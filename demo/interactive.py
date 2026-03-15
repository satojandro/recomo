"""
Interactive mode: human ↔ agent in the terminal with live coherence metrics and drift alerts.

Loop: read user input → agent responds → run pipeline on full trace → print live metrics and alerts.
"""

import sys
from typing import List

from recomo.trace_schema import ReasoningTrace, Turn

# Default task and system prompt when user does not provide one
DEFAULT_TASK = "Interactive planning session. Follow any constraints you state."
DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful planning assistant. State any constraints you will follow, "
    "then reason step by step. Keep your responses concise but complete."
)


def _turns_to_api_messages(turns: List[Turn]) -> List[dict]:
    """Convert ReCoMo turns to API format (role 'assistant' not 'agent')."""
    out: List[dict] = []
    for t in turns:
        role = "assistant" if t.role == "agent" else t.role
        out.append({"role": role, "content": t.content or ""})
    return out


def _print_live_metrics(report: dict) -> None:
    """Print live summary: extraction counts, coherence (last turn), and all alert types."""
    if "error" in report:
        print("  [Pipeline error]", report["error"][:200])
        sys.stdout.flush()
        return
    extraction = report.get("extraction") or {}
    goals = len(extraction.get("goals") or [])
    constraints = len(extraction.get("constraints") or [])
    entities = len(extraction.get("entities") or [])
    decisions = len(extraction.get("decisions") or [])
    assumptions = len(extraction.get("assumptions") or [])
    tensions = len(extraction.get("tensions") or [])
    print(
        f"  Signals: {goals} goals, {constraints} constraints, {entities} entities, "
        f"{decisions} decisions, {assumptions} assumptions, {tensions} tensions"
    )
    trajectory = report.get("trajectory") or []
    if trajectory:
        t = trajectory[-1]
        print(
            "  Coherence (last turn): "
            f"overall={t.get('overall_coherence', 0):.3f} "
            f"consistency={t.get('internal_consistency', 0):.3f} "
            f"constraint_integrity={t.get('constraint_integrity', 0):.3f} "
            f"stability={t.get('relationship_stability', 0):.3f}"
        )
    drifts = report.get("drifts") or []
    goal_drifts = report.get("goal_drifts") or []
    decision_conflicts = report.get("decision_conflicts") or []
    assumption_drifts = report.get("assumption_drifts") or []
    instability_alerts = report.get("instability_alerts") or []
    if drifts:
        for d in drifts:
            print(f"  ALERT (constraint): turn {d.get('turn')} — {d.get('severity', '')} — {(d.get('constraint_content') or '')[:60]}...")
    if goal_drifts:
        for d in goal_drifts:
            print(f"  ALERT (goal): turn {d.get('turn')} — {(d.get('goal_content') or '')[:60]}...")
    if decision_conflicts:
        for c in decision_conflicts:
            print(f"  ALERT (decision conflict): turn {c.get('turn')} — {c.get('decision_a_id')} <-> {c.get('decision_b_id')} ({c.get('tension_type', '')})")
    if assumption_drifts:
        for d in assumption_drifts:
            print(f"  ALERT (assumption): turn {d.get('turn')} — {d.get('severity', '')} — {(d.get('assumption_content') or '')[:60]}...")
    if instability_alerts:
        for a in instability_alerts:
            print(f"  ALERT (instability): turn {a.get('turn')} — stability={a.get('stability', 0):.3f} — {a.get('severity', '')}")
    if not (drifts or goal_drifts or decision_conflicts or assumption_drifts or instability_alerts):
        print("  Drifts: 0")
    print()
    sys.stdout.flush()


def run_interactive(
    task: str = DEFAULT_TASK,
    system_prompt: str | None = None,
    model: str | None = None,
    prompt_for_setup: bool = True,
) -> None:
    """
    Run an interactive session: prompt for user input, get agent response,
    run the coherence pipeline on the full trace, print live metrics and drift alerts.
    Type 'quit' or 'exit' to end the session.
    If prompt_for_setup is True, optionally prompt for task and system prompt (Enter to use defaults).
    """
    from recomo.demo.agent_adapter import get_next_agent_response
    from recomo.demo.run_demo import run_pipeline

    turns: List[Turn] = []
    turn_number = 1

    if prompt_for_setup:
        try:
            task_in = input(f"Task/context [default: {DEFAULT_TASK[:50]}...]: ").strip() or task
            if task_in:
                task = task_in
            sys_in = input("System prompt for agent (optional, Enter to skip): ").strip()
            if sys_in:
                system_prompt = sys_in
        except (EOFError, KeyboardInterrupt):
            pass
        print()

    if system_prompt:
        turns.append(Turn(turn_number=turn_number, role="system", content=system_prompt))
        turn_number += 1

    print("ReCoMo interactive mode. Type your message and press Enter. Type 'quit' or 'exit' to end.")
    print()
    sys.stdout.flush()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Ending session.")
            break

        turns.append(Turn(turn_number=turn_number, role="user", content=user_input))
        turn_number += 1

        messages = _turns_to_api_messages(turns)
        # #region agent log
        try:
            _logpath = __import__("pathlib").Path(__file__).resolve().parent.parent / ".cursor" / "debug-66406c.log"
            _t = turns[-1] if turns else None
            _logpath.parent.mkdir(parents=True, exist_ok=True)
            open(_logpath, "a").write(
                __import__("json").dumps({"sessionId": "66406c", "hypothesisId": "H3", "location": "interactive.py:before get_next", "message": "turns passed to adapter", "data": {"n_turns": len(turns), "n_messages": len(messages), "last_turn_role": _t.role if _t else None, "last_turn_content_len": len((_t.content or "")) if _t else 0}, "timestamp": __import__("time").time() * 1000}) + "\n"
            )
        except Exception:
            pass
        # #endregion
        print("Agent: ", end="")
        sys.stdout.flush()
        try:
            content = get_next_agent_response(messages, model=model)
        except Exception as e:
            print(f"[Error: {e}]")
            sys.stdout.flush()
            turns.pop()
            turn_number -= 1
            continue
        # #region agent log
        try:
            _logpath = __import__("pathlib").Path(__file__).resolve().parent.parent / ".cursor" / "debug-66406c.log"
            _logpath.parent.mkdir(parents=True, exist_ok=True)
            open(_logpath, "a").write(
                __import__("json").dumps({"sessionId": "66406c", "hypothesisId": "H3,H5", "location": "interactive.py:after get_next", "message": "content to print", "data": {"content_len": len(content), "content_preview": repr(content[:100]) if content else ""}, "timestamp": __import__("time").time() * 1000}) + "\n"
            )
        except Exception:
            pass
        # #endregion
        print(content)
        print()
        sys.stdout.flush()

        turns.append(Turn(turn_number=turn_number, role="agent", content=content))
        turn_number += 1

        trace = ReasoningTrace(
            trace_id="interactive_session",
            agent_name="InteractiveAgent",
            task=task,
            turns=turns.copy(),
        )
        report = run_pipeline(trace)
        print("--- Live metrics ---")
        _print_live_metrics(report)
