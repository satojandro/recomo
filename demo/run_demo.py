"""
End-to-end ReCoMo pipeline: extract -> graph -> coherence -> drift report.

Usage:
  python -m recomo.demo.run_demo                  # synthetic trace
  python -m recomo.demo.run_demo --real           # run real agent chain then analyze
  python -m recomo.demo.run_demo --simulate path  # run scenario then analyze
  python -m recomo.demo.run_demo --interactive   # human ↔ agent, live metrics
  python -m recomo.demo.run_demo path/to/inspect.json  # Inspect AI trace file
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv
from tqdm import tqdm

from recomo.trace_schema import ReasoningTrace
from recomo.extractor import ClaimExtractor
from recomo.graph import RelationalGraph
from recomo.checker import CoherenceTracker, DriftDetector
from recomo.adapters.inspect_ai import inspect_trace_to_reasoning_trace
from recomo.demo.traces import PROCUREMENT_TRACE
from recomo.demo.real_agent_chain import run_planning_agent_chain
from recomo.simulator import run_scenario
from recomo.demo.interactive import run_interactive


def load_trace(source: str) -> ReasoningTrace:
    """Load trace from 'synthetic', 'real', or a path to Inspect AI JSON."""
    if source == "synthetic":
        return PROCUREMENT_TRACE
    if source == "real":
        return run_planning_agent_chain(print_live=True)
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Trace file not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return inspect_trace_to_reasoning_trace(data)


def run_pipeline(
    trace: ReasoningTrace,
    progress_callback: Callable[[str, int, int], None] | None = None,
) -> dict:
    """Run extractor -> graph -> coherence tracker -> drift detector. Return report dict."""
    total_steps = 4
    try:
        if progress_callback:
            progress_callback("Extracting signals", 1, total_steps)
        extractor = ClaimExtractor()
        extraction = extractor.extract(trace)
        if "error" in extraction:
            return {"error": extraction["error"], "raw": extraction.get("raw", "")}

        if progress_callback:
            progress_callback("Building graph", 2, total_steps)
        graph = RelationalGraph()
        graph.load_extraction(extraction)
        tracker = CoherenceTracker(graph)
        tracker.compute_trajectory()

        if progress_callback:
            progress_callback("Computing coherence", 3, total_steps)
        detector = DriftDetector(graph, tracker)
        drifts = detector.detect()
        goal_drifts = detector.detect_goal_drift()
        decision_conflicts = detector.detect_decision_conflicts()
        assumption_drifts = detector.detect_assumption_drift()
        instability_alerts = detector.detect_instability()

        if progress_callback:
            progress_callback("Detecting drift", 4, total_steps)
        return {
            "extraction": extraction,
            "trajectory": tracker.get_trajectory(),
            "drifts": drifts,
            "goal_drifts": goal_drifts,
            "decision_conflicts": decision_conflicts,
            "assumption_drifts": assumption_drifts,
            "instability_alerts": instability_alerts,
        }
    except Exception as e:
        return {"error": str(e), "raw": ""}


def print_conversation(trace: ReasoningTrace, max_content_chars: int = 600) -> None:
    """Print each turn of the conversation (role + content, truncated)."""
    print("--- Conversation ---")
    for turn in trace.turns:
        content = (turn.content or "").strip()
        if len(content) > max_content_chars:
            content = content[:max_content_chars] + "..."
        role = turn.role.upper()
        print(f"[Turn {turn.turn_number}] {role}:")
        if content:
            print(content)
        print()
    sys.stdout.flush()


def print_report(report: dict, trace_source: str) -> None:
    """Print coherence report to stdout."""
    if "error" in report:
        print("EXTRACTION ERROR:", report["error"])
        if report.get("raw"):
            print("Raw response (first 500 chars):", report["raw"][:500])
        sys.stdout.flush()
        return

    extraction = report.get("extraction") or {}
    trajectory = report.get("trajectory") or []
    drifts = report.get("drifts") or []
    goal_drifts = report.get("goal_drifts") or []
    decision_conflicts = report.get("decision_conflicts") or []
    assumption_drifts = report.get("assumption_drifts") or []
    instability_alerts = report.get("instability_alerts") or []

    print("=" * 60)
    print("ReCoMo — Relational Coherence Monitor")
    print("=" * 60)
    print(f"Trace source: {trace_source}")
    print()
    print("[EXTRACTED SIGNALS]")
    for key in ("goals", "constraints", "entities", "decisions", "assumptions", "tensions"):
        items = extraction.get(key) or []
        print(f"  {key}: {len(items)}")
        for it in items[:3]:
            if key == "tensions":
                line = f"    - {it.get('element_a_id') or it.get('element_a', '')} <-> {it.get('element_b_id') or it.get('element_b', '')}: {it.get('tension_type', '')} (severity={it.get('severity')})"
            else:
                line = f"    - {it.get('id', '')}: {str(it.get('content', ''))[:60]}..."
                if key == "goals" and "connection_strength" in it:
                    line += f" (connection_strength={it.get('connection_strength')})"
                elif key == "constraints" and ("is_hard" in it or "tension_level" in it):
                    extras = []
                    if "is_hard" in it:
                        extras.append(f"is_hard={it.get('is_hard')}")
                    if "tension_level" in it:
                        extras.append(f"tension_level={it.get('tension_level')}")
                    if extras:
                        line += " [" + ", ".join(extras) + "]"
                elif key == "assumptions" and ("uncertainty_if_wrong" in it or "is_verified" in it):
                    extras = []
                    if "uncertainty_if_wrong" in it:
                        extras.append(f"uncertainty_if_wrong={it.get('uncertainty_if_wrong')}")
                    if "is_verified" in it:
                        extras.append(f"is_verified={it.get('is_verified')}")
                    if extras:
                        line += " [" + ", ".join(str(x) for x in extras) + "]"
            print(line)
        if len(items) > 3:
            print(f"    ... and {len(items) - 3} more")
    print()
    print("[COHERENCE TRAJECTORY]")
    print("  turn | internal_consistency | constraint_integrity | relationship_stability | overall_coherence")
    for t in trajectory:
        print(f"  {t['turn']:4} | {t['internal_consistency']:.3f} | {t['constraint_integrity']:.3f} | {t['relationship_stability']:.3f} | {t['overall_coherence']:.3f}")
    print()
    print("=" * 60)
    if drifts:
        print("ALERT: CONSTRAINT ABANDONMENT / DRIFT DETECTED")
        for d in drifts:
            print(f"  Turn {d['turn']}: {d['severity']} severity")
            print(f"    Constraint: {d['constraint_content'][:70]}...")
            print(f"    Violated by: {d['decision_content'][:70]}...")
            print(f"    Coherence drop: {d.get('coherence_drop', 0):.3f}")
    else:
        print("No constraint drift detected.")
    if goal_drifts:
        print()
        print("GOAL DRIFT")
        for d in goal_drifts:
            print(f"  Turn {d.get('turn')}: {d.get('severity', '')} — goal abandoned: {(d.get('goal_content') or '')[:60]}...")
    if decision_conflicts:
        print()
        print("DECISION CONFLICTS")
        for c in decision_conflicts:
            print(f"  Turn {c.get('turn')}: {c.get('decision_a_id')} <-> {c.get('decision_b_id')} ({c.get('tension_type', '')}, severity={c.get('severity')})")
    if assumption_drifts:
        print()
        print("ASSUMPTION DRIFT")
        for d in assumption_drifts:
            print(f"  Turn {d.get('turn')}: {d.get('severity', '')} — {(d.get('assumption_content') or '')[:60]}...")
    if instability_alerts:
        print()
        print("RELATIONSHIP INSTABILITY")
        for a in instability_alerts:
            print(f"  Turn {a.get('turn')}: stability={a.get('stability', 0):.3f} — {a.get('severity', '')}")
    if not (drifts or goal_drifts or decision_conflicts or assumption_drifts or instability_alerts):
        print("No drift detected.")
    print("=" * 60)
    sys.stdout.flush()


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run ReCoMo coherence pipeline")
    parser.add_argument(
        "source",
        nargs="?",
        default="synthetic",
        help="'synthetic' (default), 'real', or path to Inspect AI JSON file",
    )
    parser.add_argument(
        "--simulate",
        metavar="SCENARIO",
        help="Run scenario (JSON path) then analyze; overrides source",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run interactive mode: human ↔ agent with live metrics and drift alerts",
    )
    args = parser.parse_args()

    if args.interactive:
        load_dotenv()
        run_interactive()
        return

    if args.simulate is not None:
        try:
            trace = run_scenario(Path(args.simulate), print_live=True)
            source = f"simulate:{args.simulate}"
        except Exception as e:
            print("Failed to run scenario:", e, file=sys.stderr)
            sys.exit(1)
    else:
        source = args.source
        try:
            trace = load_trace(source)
        except Exception as e:
            print("Failed to load trace:", e, file=sys.stderr)
            sys.exit(1)

    if source == "real" or (args.simulate is not None):
        print()
        print_conversation(trace)
        print("--- ReCoMo analysis ---")
        print()
        sys.stdout.flush()
        with tqdm(total=4, desc="Pipeline", unit="step") as pbar:
            def on_progress(_name: str, step: int, total: int) -> None:
                pbar.set_postfix_str(_name)
                pbar.n = step
                pbar.refresh()

            report = run_pipeline(trace, progress_callback=on_progress)
            pbar.n = 4
            pbar.refresh()
    else:
        report = run_pipeline(trace)
    print_report(report, source)


if __name__ == "__main__":
    main()
