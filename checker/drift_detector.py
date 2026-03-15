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

    def _get_turn_for_decision(self, decision_id: str) -> int:
        """Return the turn number for a decision by id, or 0 if not found."""
        for d in self.graph.get_decisions():
            if d.get("id") == decision_id:
                return d.get("turn") or 0
        return 0

    def detect_goal_drift(self) -> List[Dict[str, Any]]:
        """Find goals that were abandoned (status-based, no extraction change)."""
        goals = self.graph.get_goals()
        drifts = []
        for g in goals:
            if (g.get("status") or "").lower() == "abandoned":
                drifts.append({
                    "turn": g.get("turn"),
                    "goal_id": g.get("id"),
                    "goal_content": g.get("content", ""),
                    "severity": "medium",
                })
        return drifts

    def detect_decision_conflicts(self) -> List[Dict[str, Any]]:
        """Find tensions where both elements are decisions."""
        tensions = self.graph.get_tensions()
        decision_ids = {d.get("id") for d in self.graph.get_decisions() if d.get("id")}
        conflicts = []
        for t in tensions:
            a_id = t.get("element_a_id") or t.get("element_a")
            b_id = t.get("element_b_id") or t.get("element_b")
            if a_id not in decision_ids or b_id not in decision_ids:
                continue
            turn_a = self._get_turn_for_decision(a_id)
            turn_b = self._get_turn_for_decision(b_id)
            turn = max(turn_a, turn_b)
            severity = t.get("severity")
            if severity is not None and not isinstance(severity, (int, float)):
                severity = 0.5
            conflicts.append({
                "turn": turn,
                "decision_a_id": a_id,
                "decision_b_id": b_id,
                "tension_type": t.get("tension_type"),
                "severity": severity if isinstance(severity, (int, float)) else 0.5,
            })
        return conflicts

    def detect_assumption_drift(self) -> List[Dict[str, Any]]:
        """Find assumptions that were contradicted (status violated)."""
        assumptions = self.graph.get_assumptions()
        drifts = []
        for a in assumptions:
            if (a.get("status") or "").lower() == "violated":
                uncertainty = a.get("uncertainty_if_wrong") or 0
                severity = "high" if uncertainty > 0.5 else "medium"
                drifts.append({
                    "turn": a.get("turn"),
                    "assumption_id": a.get("id"),
                    "assumption_content": a.get("content", ""),
                    "severity": severity,
                })
        return drifts

    def detect_instability(self, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Alert when relationship_stability drops below threshold."""
        trajectory = self.tracker.get_trajectory()
        if not trajectory:
            self.tracker.compute_trajectory()
            trajectory = self.tracker.get_trajectory()
        alerts = []
        for t in trajectory:
            if t["relationship_stability"] < threshold:
                stability = t["relationship_stability"]
                severity = "critical" if stability < 0.5 else "warning"
                alerts.append({
                    "turn": t["turn"],
                    "stability": stability,
                    "severity": severity,
                })
        return alerts
