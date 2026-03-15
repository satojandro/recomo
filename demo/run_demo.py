"""
End-to-end ReCoMo pipeline: extract -> graph -> coherence -> drift report.

Usage:
  python -m recomo.demo.run_demo                  # synthetic trace
  python -m recomo.demo.run_demo --real           # run real agent chain then analyze
  python -m recomo.demo.run_demo path/to/inspect.json  # Inspect AI trace file
"""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from recomo.trace_schema import ReasoningTrace
from recomo.extractor import ClaimExtractor
from recomo.graph import RelationalGraph
from recomo.checker import CoherenceTracker, DriftDetector
from recomo.adapters.inspect_ai import inspect_trace_to_reasoning_trace
from recomo.demo.traces import PROCUREMENT_TRACE
from recomo.demo.real_agent_chain import run_planning_agent_chain


def load_trace(source: str) -> ReasoningTrace:
    """Load trace from 'synthetic', 'real', or a path to Inspect AI JSON."""
    if source == "synthetic":
        return PROCUREMENT_TRACE
    if source == "real":
        return run_planning_agent_chain()
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Trace file not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return inspect_trace_to_reasoning_trace(data)


def run_pipeline(trace: ReasoningTrace) -> dict:
    """Run extractor -> graph -> coherence tracker -> drift detector. Return report dict."""
    try:
        extractor = ClaimExtractor()
        extraction = extractor.extract(trace)
        if "error" in extraction:
            return {"error": extraction["error"], "raw": extraction.get("raw", "")}

        graph = RelationalGraph()
        graph.load_extraction(extraction)
        tracker = CoherenceTracker(graph)
        tracker.compute_trajectory()
        detector = DriftDetector(graph, tracker)
        drifts = detector.detect()

        return {
            "extraction": extraction,
            "trajectory": tracker.get_trajectory(),
            "drifts": drifts,
        }
    except Exception as e:
        return {"error": str(e), "raw": ""}


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
    args = parser.parse_args()
    source = args.source

    try:
        trace = load_trace(source)
    except Exception as e:
        print("Failed to load trace:", e, file=sys.stderr)
        sys.exit(1)

    report = run_pipeline(trace)
    print_report(report, source)


if __name__ == "__main__":
    main()
