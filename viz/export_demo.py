"""
Export pipeline result to static JSON for the graph visualization demo.

Usage:
  python -m recomo.viz.export_demo              # synthetic trace (default)
  python -m recomo.viz.export_demo path/to.json  # Inspect AI trace file

Writes viz/demo_output.json. Then open viz/index.html (or serve viz/ with a static server).
"""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from recomo.demo.run_demo import load_trace, run_pipeline
from recomo.graph import RelationalGraph


def _edge_turn(edge: dict) -> int:
    """Derive turn for an edge for replay visibility."""
    d = edge.get("decision")
    if d is not None and isinstance(d, dict):
        t = d.get("turn")
        if t is not None:
            return int(t)
    t = edge.get("tension")
    if t is not None and isinstance(t, dict) and t.get("turn") is not None:
        return int(t["turn"])
    return 0


def serialize_payload(report: dict, trace) -> dict:
    """Build frontend payload from report and trace. Rebuilds graph from extraction."""
    if report.get("error"):
        return {
            "error": report["error"],
            "trace": _serialize_trace(trace),
            "nodes": [],
            "edges": [],
            "trajectory": [],
            "drifts": [],
            "goal_drifts": [],
            "decision_conflicts": [],
            "assumption_drifts": [],
            "instability_alerts": [],
        }
    extraction = report.get("extraction") or {}
    graph = RelationalGraph()
    graph.load_extraction(extraction)

    nodes = []
    for n in graph.get_nodes():
        nid = n.get("id") or ""
        content = (n.get("content") or "").strip()
        label = content[:60] + "..." if len(content) > 60 else content
        nodes.append({
            "id": nid,
            "type": n.get("type", ""),
            "turn": n.get("turn") if n.get("turn") is not None else 0,
            "label": label,
            "content": content,
        })

    edges = []
    for e in graph.get_edges():
        turn = _edge_turn(e)
        edges.append({
            "source": e.get("source", ""),
            "target": e.get("target", ""),
            "type": e.get("type", ""),
            "turn": turn,
        })

    return {
        "trace": _serialize_trace(trace),
        "nodes": nodes,
        "edges": edges,
        "trajectory": report.get("trajectory") or [],
        "drifts": report.get("drifts") or [],
        "goal_drifts": report.get("goal_drifts") or [],
        "decision_conflicts": report.get("decision_conflicts") or [],
        "assumption_drifts": report.get("assumption_drifts") or [],
        "instability_alerts": report.get("instability_alerts") or [],
    }


def _serialize_trace(trace) -> dict:
    """Serialize trace for frontend (turns with turn_number, role, content)."""
    return {
        "trace_id": getattr(trace, "trace_id", ""),
        "task": getattr(trace, "task", ""),
        "turns": [
            {
                "turn_number": getattr(t, "turn_number", i + 1),
                "role": getattr(t, "role", ""),
                "content": getattr(t, "content", ""),
            }
            for i, t in enumerate(getattr(trace, "turns", []))
        ],
    }


def export_report_and_trace(report: dict, trace, out_path: Path | None = None) -> Path:
    """
    Serialize report + trace to JSON and write to out_path (default: viz/demo_output.json).
    Used by live_session to overwrite the file after each turn.
    Returns the path written.
    """
    payload = serialize_payload(report, trace)
    if out_path is None:
        out_path = Path(__file__).resolve().parent / "demo_output.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return out_path


def main() -> None:
    load_dotenv()

    source = "synthetic"
    if len(sys.argv) > 1:
        source = sys.argv[1].strip()

    trace = load_trace(source)
    report = run_pipeline(trace)
    payload = serialize_payload(report, trace)

    out_dir = Path(__file__).resolve().parent
    out_path = out_dir / "demo_output.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    if report.get("error"):
        print("Pipeline had an error; wrote partial payload.", file=sys.stderr)
        print(report["error"], file=sys.stderr)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
