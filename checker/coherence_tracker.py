"""
Numeric coherence metrics and turn-by-turn trajectory.

Formula: overall_coherence = 0.4 * internal_consistency + 0.4 * constraint_integrity + 0.2 * relationship_stability
"""

from typing import Any, Dict, List

from recomo.graph.relational_graph import RelationalGraph

# Weights for overall_coherence (must sum to 1.0)
WEIGHT_INTERNAL_CONSISTENCY = 0.4
WEIGHT_CONSTRAINT_INTEGRITY = 0.4
WEIGHT_RELATIONSHIP_STABILITY = 0.2


class CoherenceTracker:
    """Computes internal_consistency, constraint_integrity, relationship_stability, and overall_coherence per turn."""

    def __init__(self, graph: RelationalGraph):
        self.graph = graph
        self._trajectory: List[Dict[str, Any]] = []

    def compute_trajectory(self, max_turn: int | None = None) -> List[Dict[str, Any]]:
        """
        Compute coherence scores turn-by-turn.
        Returns list of {turn, internal_consistency, constraint_integrity, relationship_stability, overall_coherence}.
        """
        constraints = self.graph.get_constraints()
        decisions = self.graph.get_decisions()
        contradictions = self.graph.get_contradictions()
        edges = self.graph.get_edges()

        turns_seen = set()
        for c in constraints:
            t = c.get("turn")
            if t is not None:
                turns_seen.add(t)
        for d in decisions:
            t = d.get("turn")
            if t is not None:
                turns_seen.add(t)
        if not turns_seen:
            turns_seen = {1}
        ordered_turns = sorted(turns_seen)
        if max_turn is not None:
            ordered_turns = [t for t in ordered_turns if t <= max_turn]

        self._trajectory = []
        for turn in ordered_turns:
            ic = self._internal_consistency_at_turn(constraints, decisions, turn)
            ci = self._constraint_integrity_at_turn(constraints, decisions, contradictions, turn)
            rs = self._relationship_stability_at_turn(edges, contradictions, turn)
            overall = (
                WEIGHT_INTERNAL_CONSISTENCY * ic
                + WEIGHT_CONSTRAINT_INTEGRITY * ci
                + WEIGHT_RELATIONSHIP_STABILITY * rs
            )
            self._trajectory.append({
                "turn": turn,
                "internal_consistency": round(ic, 4),
                "constraint_integrity": round(ci, 4),
                "relationship_stability": round(rs, 4),
                "overall_coherence": round(overall, 4),
            })
        return self._trajectory

    def _internal_consistency_at_turn(
        self,
        constraints: List[Dict],
        decisions: List[Dict],
        turn: int,
    ) -> float:
        """Do goals/constraints and decisions up to this turn align? 1.0 = no contradictions."""
        constraints_up_to = [c for c in constraints if (c.get("turn") or 0) <= turn]
        decisions_up_to = [d for d in decisions if (d.get("turn") or 0) <= turn]
        violated = sum(1 for d in decisions_up_to if (d.get("status") or "").lower() == "violated")
        total_decisions = len(decisions_up_to) or 1
        # Fraction of decisions that do not violate
        return 1.0 - (violated / total_decisions)

    def _constraint_integrity_at_turn(
        self,
        constraints: List[Dict],
        decisions: List[Dict],
        contradictions: List[Dict],
        turn: int,
    ) -> float:
        """Are stated constraints respected by decisions up to this turn? 1.0 = all respected."""
        constraints_up_to = [c for c in constraints if (c.get("turn") or 0) <= turn]
        violations_up_to = [
            x for x in contradictions
            if (x.get("decision", {}).get("turn") or 0) <= turn
        ]
        total_constraints = len(constraints_up_to) or 1
        violated_count = len(set(v.get("constraint", {}).get("id") for v in violations_up_to))
        return max(0.0, 1.0 - (violated_count / total_constraints))

    def _relationship_stability_at_turn(
        self,
        edges: List[Dict],
        contradictions: List[Dict],
        turn: int,
    ) -> float:
        """Stability of relationships up to this turn: fewer violations = higher. 1.0 = no violations."""
        violations_up_to = [
            x for x in contradictions
            if (x.get("decision", {}).get("turn") or 0) <= turn
        ]
        total_edges_up_to = len([e for e in edges if (e.get("decision", {}).get("turn") or 0) <= turn])
        if total_edges_up_to == 0:
            return 1.0
        violate_edges = len([e for e in edges if e.get("type") == "violates" and (e.get("decision", {}).get("turn") or 0) <= turn])
        ratio = violate_edges / max(total_edges_up_to, 1)
        return max(0.0, 1.0 - ratio)

    def get_trajectory(self) -> List[Dict[str, Any]]:
        """Return the last computed trajectory."""
        return list(self._trajectory)
