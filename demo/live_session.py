"""
Live session: interactive conversation with graph viz updating in real time.

Same loop as interactive mode, but after each exchange overwrites viz/demo_output.json
so the browser (polling) can show the graph evolving as you talk.

Usage:
  python -m recomo.demo.live_session

Then open viz/index.html?live=1 (or serve viz/ and add ?live=1) to see the graph update.
"""

import sys
from pathlib import Path
from typing import List

from dotenv import load_dotenv

from recomo.trace_schema import ReasoningTrace, Turn

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
    """Print live summary: extraction counts, coherence, drift alerts."""
    if "error" in report:
        print("  [Pipeline error]", report["error"][:200])
        sys.stdout.flush()
        return
    extraction = report.get("extraction") or {}
    goals = len(extraction.get("goals") or [])
    constraints = len(extraction.get("constraints") or [])
    decisions = len(extraction.get("decisions") or [])
    print(f"  Signals: {goals} goals, {constraints} constraints, {decisions} decisions")
    trajectory = report.get("trajectory") or []
    if trajectory:
        t = trajectory[-1]
        print(f"  Coherence: {t.get('overall_coherence', 0):.3f}")
    drifts = report.get("drifts") or []
    if drifts:
        for d in drifts[:2]:
            print(f"  ALERT: turn {d.get('turn')} — {(d.get('constraint_content') or '')[:50]}...")
    else:
        print("  Drifts: 0")
    print()
    sys.stdout.flush()


def run_live_session(
    task: str = DEFAULT_TASK,
    system_prompt: str | None = None,
    model: str | None = None,
    prompt_for_setup: bool = True,
) -> None:
    """
    Interactive session that overwrites viz/demo_output.json after each exchange.
    Open viz with ?live=1 to poll and see the graph update in real time.
    """
    from recomo.demo.agent_adapter import get_next_agent_response
    from recomo.demo.run_demo import run_pipeline
    from recomo.viz.export_demo import export_report_and_trace

    load_dotenv()

    viz_dir = Path(__file__).resolve().parent.parent / "viz"
    out_path = viz_dir / "demo_output.json"

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

    print("ReCoMo LIVE mode — graph updates at viz/ as you chat. Type 'quit' to end.")
    print("Open viz/index.html?live=1 (serve viz/ with: python -m http.server 8080)")
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
        print(content)
        print()
        sys.stdout.flush()

        turns.append(Turn(turn_number=turn_number, role="agent", content=content))
        turn_number += 1

        trace = ReasoningTrace(
            trace_id="live_session",
            agent_name="LiveAgent",
            task=task,
            turns=turns.copy(),
        )
        report = run_pipeline(trace)
        export_report_and_trace(report, trace, out_path=out_path)
        print("--- Live metrics (viz updated) ---")
        _print_live_metrics(report)


if __name__ == "__main__":
    run_live_session()
