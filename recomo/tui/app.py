"""
ReCoMo TUI: conversation pane, coherence metrics table, and drift alerts.

Supports replay (load trace from file or synthetic) and interactive mode (chat in TUI;
metrics and alerts update live). First load shows ASCII welcome and instructions.
"""

from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Container, ScrollableContainer, Vertical
from textual.widgets import DataTable, Header, Input, Static
from textual import work

# Defaults for interactive mode (same as demo/interactive.py)
DEFAULT_TASK = "Interactive planning session. Follow any constraints you state."
DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful planning assistant. State any constraints you will follow, "
    "then reason step by step. Keep your responses concise but complete."
)

# Block-style ASCII logo with cyan styling for visual hierarchy
WELCOME_ASCII = r"""[bold cyan]██████╗ ███████╗ ██████╗ ██████╗ ███╗   ███╗ ██████╗ 
██╔══██╗██╔════╝██╔════╝██╔═══██╗████╗ ████║██╔═══██╗
██████╔╝█████╗  ██║     ██║   ██║██╔████╔██║██║   ██║
██╔══██╗██╔══╝  ██║     ██║   ██║██║╚██╔╝██║██║   ██║
██║  ██║███████╗╚██████╗╚██████╔╝██║ ╚═╝ ██║╚██████╔╝
╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝     ╚═╝ ╚═════╝

      Relational Coherence Monitor[/bold cyan]

[dim][italic]Observe reasoning • Measure coherence • Detect drift[/italic][/dim]


[bold]What is ReCoMo?[/bold]

ReCoMo tracks how an AI reasons over time.

Instead of scoring only final answers, it monitors the
relationships inside reasoning:

• Goals
• Constraints
• Decisions
• Assumptions

When those relationships break, ReCoMo raises drift alerts.


[bold]Why it matters[/bold]

Most evaluation tools score outputs.

ReCoMo monitors the reasoning trajectory itself —
surfacing inconsistencies the moment they appear.


[bold]Instructions[/bold]

Type a message below and press [bold]Enter[/bold].

The agent replies and ReCoMo updates:

• Coherence metrics
• Drift alerts
• Reasoning trajectory


[dim]────────────────────────────────────────────────────[/dim]
"""


def _run_pipeline(trace: "Any") -> dict:
    from recomo.demo.run_demo import run_pipeline
    return run_pipeline(trace)


def _turns_to_api_messages(turns: list) -> list:
    """ReCoMo turns → API format (role 'assistant' not 'agent')."""
    out = []
    for t in turns:
        role = "assistant" if getattr(t, "role", None) == "agent" else getattr(t, "role", "user")
        out.append({"role": role, "content": getattr(t, "content", "") or ""})
    return out


INITIALIZING_MESSAGE = "Initializing relational monitor..."

def _format_conversation(trace: "Any", show_welcome: bool = False, initializing: bool = False) -> str:
    if initializing:
        return INITIALIZING_MESSAGE
    if show_welcome:
        return WELCOME_ASCII
    if trace is None or not getattr(trace, "turns", None):
        return "No trace loaded. Run with a trace file path or use interactive mode."
    lines = []
    for t in trace.turns:
        role = (getattr(t, "role", "") or "").upper()
        content = (getattr(t, "content", "") or "").strip()
        if len(content) > 400:
            content = content[:400] + "..."
        lines.append(f"[Turn {t.turn_number}] {role}:")
        if content:
            lines.append(content)
        lines.append("")
    return "\n".join(lines) if lines else "No turns."


def _format_pipeline_error(report: dict) -> str:
    """User-friendly message when pipeline/extraction fails."""
    err = (report or {}).get("error", "Unknown error")
    if "parse extraction" in err.lower() or "json" in err.lower():
        return (
            "Extraction failed: LLM returned invalid JSON.\n\n"
            "Check OPENROUTER_API_KEY and RECOMO_LLM_MODEL in .env"
        )
    return err[:300] if err else "Pipeline error"


def _count_drift_alerts(report: dict) -> int:
    """Total count of all drift-related alerts."""
    if not report or "error" in report:
        return 0
    return (
        len(report.get("drifts") or [])
        + len(report.get("goal_drifts") or [])
        + len(report.get("decision_conflicts") or [])
        + len(report.get("assumption_drifts") or [])
        + len(report.get("instability_alerts") or [])
    )


def _format_live_metrics(report: dict) -> str:
    """Format current turn's coherence metrics and drift count for live display."""
    if not report or "error" in report:
        return _format_pipeline_error(report)
    trajectory = report.get("trajectory") or []
    if not trajectory:
        return "No trajectory yet."
    latest = trajectory[-1]
    turn = latest.get("turn", "?")
    overall = latest.get("overall_coherence", 0)
    consistency = latest.get("internal_consistency", 0)
    constraint_int = latest.get("constraint_integrity", 0)
    stability = latest.get("relationship_stability", 0)
    drift_count = _count_drift_alerts(report)
    return (
        f"Turn: {turn}\n"
        f"Overall:      {overall:.3f}\n"
        f"Consistency:  {consistency:.3f}\n"
        f"Constraint:   {constraint_int:.3f}\n"
        f"Stability:    {stability:.3f}\n"
        f"Drift:        {drift_count}"
    )


def _format_alerts(report: dict) -> str:
    if not report or "error" in report:
        return _format_pipeline_error(report)
    lines = []
    for d in report.get("drifts") or []:
        lines.append(f"Constraint (turn {d.get('turn')}): {d.get('severity', '')} — {(d.get('constraint_content') or '')[:50]}...")
    for d in report.get("goal_drifts") or []:
        lines.append(f"Goal (turn {d.get('turn')}): {(d.get('goal_content') or '')[:50]}...")
    for c in report.get("decision_conflicts") or []:
        lines.append(f"Decision conflict (turn {c.get('turn')}): {c.get('decision_a_id')} <-> {c.get('decision_b_id')}")
    for d in report.get("assumption_drifts") or []:
        lines.append(f"Assumption (turn {d.get('turn')}): {(d.get('assumption_content') or '')[:50]}...")
    for a in report.get("instability_alerts") or []:
        lines.append(f"Instability (turn {a.get('turn')}): stability={a.get('stability', 0):.3f} — {a.get('severity', '')}")
    if not lines:
        return "No warnings."
    return "\n".join(lines)


class ReComoTui(App[None]):
    """TUI: conversation (left), metrics table + alerts (right)."""

    TITLE = "ReCoMo — Relational Coherence Monitor"
    CSS = """
    Screen {
        layout: vertical;
    }
    #main {
        layout: horizontal;
        height: 1fr;
    }
    #left {
        width: 1fr;
        min-width: 20;
        border: solid $secondary;
        padding: 0 1;
    }
    #right {
        width: 40;
        min-width: 30;
        border: solid $secondary;
        padding: 0 1;
        layout: vertical;
    }
    #conversation {
        height: 1fr;
        overflow-y: auto;
        padding: 0 1;
    }
    #live_metrics {
        height: auto;
        min-height: 8;
        padding: 0 1;
        border: solid $primary;
    }
    #metrics {
        height: 10;
        padding: 0 1;
        border: solid $primary;
    }
    #alerts {
        height: 1fr;
        overflow-y: auto;
        padding: 0 1;
    }
    .panel-title {
        text-style: bold;
        color: $accent;
    }
    #chat_input {
        width: 1fr;
        margin-top: 1;
    }
    Screen.replay #chat_input {
        display: none;
    }
    """

    def __init__(self, trace_path: str | Path | None = None) -> None:
        super().__init__()
        self._trace_path = Path(trace_path) if trace_path else None
        self._trace: Any = None
        self._report: dict = {}
        self._interactive_mode = trace_path is None or not Path(trace_path).exists()
        self._show_welcome = self._interactive_mode
        self._initializing = self._interactive_mode  # Startup animation only in interactive mode

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main"):
            with Vertical(id="left"):
                yield Static("Conversation", classes="panel-title")
                with ScrollableContainer(id="conversation_scroll"):
                    yield Static("Loading...", id="conversation")
                yield Input(placeholder="Type your message and press Enter to chat...", id="chat_input")
            with Vertical(id="right"):
                yield Static("Live metrics", classes="panel-title")
                yield Static("—", id="live_metrics")
                yield Static("Coherence (per turn)", classes="panel-title")
                yield DataTable(id="metrics")
                yield Static("Warnings", classes="panel-title")
                with ScrollableContainer():
                    yield Static("No warnings.", id="alerts")

    def on_mount(self) -> None:
        self.query_one("#metrics", DataTable).add_columns("turn", "overall", "consistency", "constraint_int", "stability")
        if not self._interactive_mode and self._trace_path and self._trace_path.exists():
            self.add_class("replay")
            self.load_trace_from_path(self._trace_path)
        else:
            # Interactive mode: show "Initializing..." then welcome after 0.5s
            from recomo.trace_schema import ReasoningTrace, Turn
            self._trace = ReasoningTrace(
                trace_id="tui_interactive",
                agent_name="TUI",
                task=DEFAULT_TASK,
                turns=[Turn(turn_number=1, role="system", content=DEFAULT_SYSTEM_PROMPT)],
            )
            self._report = _run_pipeline(self._trace)
            self._refresh_ui()
            self.set_timer(0.5, self._show_welcome_screen)

    def _show_welcome_screen(self) -> None:
        """Called after 0.5s delay: replace 'Initializing...' with full welcome."""
        self._initializing = False
        self._show_welcome = True
        self._refresh_ui()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if not self._interactive_mode or self._trace is None:
            return
        value = (event.value or "").strip()
        if not value:
            return
        event.input.value = ""
        self._show_welcome = False
        # Run blocking work in a background thread; refresh UI on main thread when done.
        import threading
        def run_then_refresh() -> None:
            try:
                self._do_handle_user_message(value)
            except Exception as e:
                self._report = {"error": f"Chat failed: {e!r}"}
            self.call_from_thread(self._refresh_ui)
        threading.Thread(target=run_then_refresh, daemon=True).start()

    def _do_handle_user_message(self, user_text: str) -> None:
        """Blocking: get agent response and run pipeline (called from background thread)."""
        from recomo.trace_schema import ReasoningTrace, Turn
        from recomo.demo.agent_adapter import get_next_agent_response
        turns = list(self._trace.turns)
        turn_number = len(turns) + 1
        turns.append(Turn(turn_number=turn_number, role="user", content=user_text))
        messages = _turns_to_api_messages(turns)
        content = get_next_agent_response(messages)
        turns.append(Turn(turn_number=turn_number + 1, role="agent", content=content))
        self._trace = ReasoningTrace(
            trace_id=self._trace.trace_id,
            agent_name=self._trace.agent_name,
            task=self._trace.task,
            turns=turns,
        )
        self._report = _run_pipeline(self._trace)

    @work(thread=True)
    def load_trace_from_path(self, path: Path) -> None:
        from recomo.trace_schema import ReasoningTrace
        from recomo.adapters.inspect_ai import inspect_trace_to_reasoning_trace
        import json
        p = Path(path)
        if not p.exists():
            self._report = {"error": f"File not found: {p}"}
            self.call_from_thread(self._refresh_ui)
            return
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        trace = inspect_trace_to_reasoning_trace(data)
        self._trace = trace
        self._report = _run_pipeline(trace)
        self.call_from_thread(self._refresh_ui)

    def set_trace(self, trace: "Any") -> None:
        """Set trace and run pipeline (call from main thread or use run_worker)."""
        self._trace = trace
        self._report = _run_pipeline(trace)
        self._refresh_ui()

    def _refresh_ui(self) -> None:
        conv = self.query_one("#conversation", Static)
        conv.update(_format_conversation(self._trace, show_welcome=self._show_welcome, initializing=self._initializing))
        # Live metrics: real-time values for current turn
        live = self.query_one("#live_metrics", Static)
        live.update(_format_live_metrics(self._report))
        dt = self.query_one("#metrics", DataTable)
        dt.clear()
        trajectory = self._report.get("trajectory") or []
        for t in trajectory:
            dt.add_row(
                t.get("turn", ""),
                f"{t.get('overall_coherence', 0):.3f}",
                f"{t.get('internal_consistency', 0):.3f}",
                f"{t.get('constraint_integrity', 0):.3f}",
                f"{t.get('relationship_stability', 0):.3f}",
            )
        alerts_widget = self.query_one("#alerts", Static)
        alerts_widget.update(_format_alerts(self._report))
        # Scroll conversation to end so new messages are visible
        try:
            scroll_container = self.query_one("#conversation_scroll", ScrollableContainer)
            scroll_container.scroll_end(animate=False)
        except Exception:
            pass


def run_tui(trace_path: str | Path | None = None) -> None:
    """Run the ReCoMo TUI. trace_path: optional path to Inspect AI JSON trace for replay."""
    app = ReComoTui(trace_path=trace_path)
    app.run()
