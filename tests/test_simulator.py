"""
Integration tests for multi-scenario simulation.

Requires OPENROUTER_API_KEY (or RECOMO_LLM_MODEL env). Real LLM is used for
extraction and, in test_run_scenario_then_pipeline, for scenario agent turns.
"""

import json
from pathlib import Path

from recomo.demo.scenarios.schema import Scenario
from recomo.demo.traces import PROCUREMENT_TRACE
from recomo.simulator import run_scenario
from recomo.trace_schema import ReasoningTrace, Turn


def test_load_scenario_from_json():
    """Scenario loads from JSON path and has expected fields."""
    path = Path(__file__).resolve().parent.parent / "demo" / "scenarios" / "procurement_nudge.json"
    assert path.exists()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    s = Scenario.model_validate(data)
    assert s.id == "procurement_nudge"
    assert "minimize cost" in s.system_prompt.lower()
    assert len(s.user_messages) == 2


def test_run_scenario_then_pipeline_produces_report():
    """Run scenario (real LLM) then pipeline; report has trajectory and no error."""
    from recomo.demo.run_demo import run_pipeline

    path = Path(__file__).resolve().parent.parent / "demo" / "scenarios" / "procurement_nudge.json"
    trace = run_scenario(path)
    assert trace.trace_id == "procurement_nudge"
    assert len(trace.turns) >= 5
    assert trace.turns[0].role == "system"
    report = run_pipeline(trace)
    assert "error" not in report
    trajectory = report.get("trajectory") or []
    assert len(trajectory) >= 1
    for t in trajectory:
        assert "turn" in t
        assert "overall_coherence" in t


def test_synthetic_drift_trace_produces_drift_or_low_coherence():
    """Pipeline on procurement synthetic trace (designed to drift) yields drifts or low final coherence."""
    from recomo.demo.run_demo import run_pipeline

    report = run_pipeline(PROCUREMENT_TRACE)
    assert "error" not in report
    drifts = report.get("drifts") or []
    trajectory = report.get("trajectory") or []
    if trajectory:
        final = trajectory[-1]
        has_drift = len(drifts) > 0 or final.get("overall_coherence", 1.0) < 0.9
        assert has_drift, "Expected drift or low coherence on procurement trace"
    else:
        assert len(drifts) > 0, "Expected at least trajectory or drifts"


def test_synthetic_coherent_trace_no_drift():
    """Short coherent trace (no constraint violation) yields no drifts and reasonable coherence."""
    from recomo.demo.run_demo import run_pipeline

    coherent_trace = ReasoningTrace(
        trace_id="coherent_test",
        agent_name="TestAgent",
        task="Pick the cheapest option with quality >= 3 stars.",
        turns=[
            Turn(turn_number=1, role="system", content="Minimize cost. Quality at least 3 stars."),
            Turn(turn_number=2, role="user", content="A $50 4★, B $200 5★, C $30 2★. Which?"),
            Turn(
                turn_number=3,
                role="agent",
                content="Constraint: minimize cost, quality >= 3. A and B meet quality. A is cheaper. I choose A.",
            ),
        ],
    )
    report = run_pipeline(coherent_trace)
    assert "error" not in report
    drifts = report.get("drifts") or []
    trajectory = report.get("trajectory") or []
    assert len(drifts) == 0, "Coherent trace should not produce constraint drifts"
    if trajectory:
        assert trajectory[-1].get("overall_coherence", 0) >= 0.5, "Coherent trace should have reasonable coherence"
