"""
In-memory relational graph built from extraction output.

Entities as nodes; relationships as edges (supports, contradicts, depends_on).
Constraints and decisions are first-class; decisions linked to affected constraints.
"""

from typing import Any, Dict, List, Optional

# Edge types for relationships between nodes
EDGE_SUPPORTS = "supports"
EDGE_CONTRADICTS = "contradicts"
EDGE_DEPENDS_ON = "depends_on"
EDGE_VIOLATES = "violates"
EDGE_SATISFIES = "satisfies"


class RelationalGraph:
    """Queryable graph of extracted goals, constraints, entities, decisions, and relationships."""

    def __init__(self):
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._edges: List[Dict[str, Any]] = []
        self._constraints: List[Dict[str, Any]] = []
        self._decisions: List[Dict[str, Any]] = []
        self._goals: List[Dict[str, Any]] = []
        self._entities: List[Dict[str, Any]] = []
        self._contradictions: List[Dict[str, Any]] = []

    def load_extraction(self, extraction: Dict[str, Any]) -> None:
        """Build graph from extraction dict (goals, constraints, entities, decisions, assumptions)."""
        self._constraints = extraction.get("constraints") or []
        self._decisions = extraction.get("decisions") or []
        self._goals = extraction.get("goals") or []
        self._entities = extraction.get("entities") or []
        assumptions = extraction.get("assumptions") or []

        self._nodes.clear()
        self._edges.clear()
        self._contradictions.clear()

        for c in self._constraints:
            nid = c.get("id") or f"constraint_{len(self._nodes)}"
            self._nodes[nid] = {"type": "constraint", **c}
        for d in self._decisions:
            nid = d.get("id") or f"decision_{len(self._nodes)}"
            self._nodes[nid] = {"type": "decision", **d}
        for g in self._goals:
            nid = g.get("id") or f"goal_{len(self._nodes)}"
            self._nodes[nid] = {"type": "goal", **g}
        for e in self._entities:
            nid = e.get("id") or f"entity_{len(self._nodes)}"
            self._nodes[nid] = {"type": "entity", **e}
        for a in assumptions:
            nid = a.get("id") or f"assumption_{len(self._nodes)}"
            self._nodes[nid] = {"type": "assumption", **a}

        # Edges: decision -> constraint (violates or satisfies by status)
        for d in self._decisions:
            did = d.get("id")
            status = (d.get("status") or "").lower()
            d_turn = d.get("turn") or 0
            if status == "violated":
                violated_constraints = [c for c in self._constraints if (c.get("status") or "").lower() == "violated"]
                if not violated_constraints:
                    # Fallback: link to constraints that appear before this decision (candidate violated)
                    violated_constraints = [c for c in self._constraints if (c.get("turn") or 0) < d_turn]
                for c in violated_constraints:
                    self._edges.append({
                        "source": did,
                        "target": c.get("id"),
                        "type": EDGE_VIOLATES,
                        "decision": d,
                        "constraint": c,
                    })
                    self._contradictions.append({"constraint": c, "decision": d})
            elif status == "satisfied":
                for c in self._constraints:
                    if (c.get("status") or "").lower() == "satisfied":
                        self._edges.append({
                            "source": did,
                            "target": c.get("id"),
                            "type": EDGE_SATISFIES,
                            "decision": d,
                            "constraint": c,
                        })

    def get_constraints(self) -> List[Dict[str, Any]]:
        """Return all constraints."""
        return list(self._constraints)

    def get_decisions_by_turn(self, turn_number: int) -> List[Dict[str, Any]]:
        """Return decisions that appeared at or before the given turn."""
        return [d for d in self._decisions if (d.get("turn") or 0) <= turn_number]

    def get_contradictions(self) -> List[Dict[str, Any]]:
        """Return constraint–decision pairs that contradict (decision violates constraint)."""
        return list(self._contradictions)

    def get_edges(self) -> List[Dict[str, Any]]:
        """Return all edges (supports, contradicts, violates, satisfies)."""
        return list(self._edges)

    def get_decisions(self) -> List[Dict[str, Any]]:
        """Return all decisions."""
        return list(self._decisions)
