"""
Drift detection: where coherence drops, with evidence and severity.
"""

from typing import Any, Dict, List

from recomo.graph.relational_graph import RelationalGraph
from recomo.checker.coherence_tracker import CoherenceTracker


class DriftDetector:
    """Identifies turns where coherence drops and produces evidence (constraint, decision, severity)."""

    def __init__(self, graph: RelationalGraph, tracker: CoherenceTracker):
        self.graph = graph
        self.tracker = tracker

    def detect(self) -> List[Dict[str, Any]]:
        """
        Return drift events: turn where drop occurred, constraint, violating decision, severity.
        """
        trajectory = self.tracker.get_trajectory()
        if not trajectory:
            self.tracker.compute_trajectory()
            trajectory = self.tracker.get_trajectory()

        contradictions = self.graph.get_contradictions()
        drifts = []
        for c in contradictions:
            constraint = c.get("constraint") or {}
            decision = c.get("decision") or {}
            turn = decision.get("turn")
            if turn is None:
                turn = constraint.get("turn") or 0
            # Severity: high if constraint was explicit (early turn), else medium
            severity = self._assess_severity(constraint, decision)
            # Coherence drop: find trajectory at this turn vs previous
            drop = self._coherence_drop_at_turn(trajectory, turn)
            drifts.append({
                "turn": turn,
                "constraint_id": constraint.get("id"),
                "constraint_content": constraint.get("content", ""),
                "violating_decision_id": decision.get("id"),
                "decision_content": decision.get("content", ""),
                "severity": severity,
                "coherence_drop": drop,
            })
        return drifts

    def _assess_severity(self, constraint: Dict, decision: Dict) -> str:
        """Rate severity (low | medium | high) from constraint/decision content."""
        content = (constraint.get("content") or "").lower()
        dec_content = (decision.get("content") or "").lower()
        if "minimize" in content or "must" in content or "required" in content:
            return "high"
        if "premium" in dec_content or "expensive" in dec_content or "worth it" in dec_content:
            return "high"
        return "medium"

    def _coherence_drop_at_turn(self, trajectory: List[Dict], turn: int) -> float:
        """Return drop in overall_coherence at this turn vs previous (positive = drop)."""
        prev_score = 1.0
        at_score = 1.0
        for t in trajectory:
            if t["turn"] < turn:
                prev_score = t["overall_coherence"]
            if t["turn"] == turn:
                at_score = t["overall_coherence"]
                break
        return max(0.0, prev_score - at_score)
