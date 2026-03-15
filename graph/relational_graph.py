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
# Tension edge types (from extraction)
EDGE_CONFLICT = "conflict"
EDGE_TRADEOFF = "tradeoff"
EDGE_AMBIGUITY = "ambiguity"


class RelationalGraph:
    """Queryable graph of extracted goals, constraints, entities, decisions, tensions, and relationships."""

    def __init__(self):
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._edges: List[Dict[str, Any]] = []
        self._constraints: List[Dict[str, Any]] = []
        self._decisions: List[Dict[str, Any]] = []
        self._goals: List[Dict[str, Any]] = []
        self._entities: List[Dict[str, Any]] = []
        self._tensions: List[Dict[str, Any]] = []
        self._contradictions: List[Dict[str, Any]] = []

    def load_extraction(self, extraction: Dict[str, Any]) -> None:
        """Build graph from extraction dict (goals, constraints, entities, decisions, assumptions, tensions)."""
        self._constraints = extraction.get("constraints") or []
        self._decisions = extraction.get("decisions") or []
        self._goals = extraction.get("goals") or []
        self._entities = extraction.get("entities") or []
        assumptions = extraction.get("assumptions") or []
        self._tensions = extraction.get("tensions") or []

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

        # Edges: decision -> constraint. Prefer explicit constraint_alignment when present.
        constraint_ids = {c.get("id") for c in self._constraints if c.get("id")}
        for d in self._decisions:
            did = d.get("id")
            alignment = d.get("constraint_alignment") or []
            if alignment:
                for item in alignment:
                    if not isinstance(item, str):
                        continue
                    parts = item.split(":", 1)
                    if len(parts) != 2:
                        continue
                    kind, cid = parts[0].strip().lower(), parts[1].strip()
                    if cid not in constraint_ids:
                        continue
                    constraint = next((c for c in self._constraints if c.get("id") == cid), None)
                    if not constraint:
                        continue
                    if kind == "violates":
                        self._edges.append({
                            "source": did,
                            "target": cid,
                            "type": EDGE_VIOLATES,
                            "decision": d,
                            "constraint": constraint,
                        })
                        self._contradictions.append({"constraint": constraint, "decision": d})
                    elif kind == "satisfies":
                        self._edges.append({
                            "source": did,
                            "target": cid,
                            "type": EDGE_SATISFIES,
                            "decision": d,
                            "constraint": constraint,
                        })
            else:
                # Fallback: infer from status (backward compatible)
                status = (d.get("status") or "").lower()
                d_turn = d.get("turn") or 0
                if status == "violated":
                    violated_constraints = [c for c in self._constraints if (c.get("status") or "").lower() == "violated"]
                    if not violated_constraints:
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

        # Edges: tensions (element_a_id <-> element_b_id with tension_type and severity)
        tension_type_to_edge = {"conflict": EDGE_CONFLICT, "tradeoff": EDGE_TRADEOFF, "ambiguity": EDGE_AMBIGUITY}
        for t in self._tensions:
            a_id = t.get("element_a_id") or t.get("element_a")
            b_id = t.get("element_b_id") or t.get("element_b")
            if not a_id or not b_id:
                continue
            edge_type = tension_type_to_edge.get((t.get("tension_type") or "").lower(), "tension")
            severity = t.get("severity")
            self._edges.append({
                "source": a_id,
                "target": b_id,
                "type": edge_type,
                "severity": severity,
                "tension": t,
            })

    def get_constraints(self) -> List[Dict[str, Any]]:
        """Return all constraints."""
        return list(self._constraints)

    def get_goals(self) -> List[Dict[str, Any]]:
        """Return all goals."""
        return list(self._goals)

    def get_assumptions(self) -> List[Dict[str, Any]]:
        """Return all assumptions (from nodes)."""
        return [n for n in self._nodes.values() if n.get("type") == "assumption"]

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

    def get_tensions(self) -> List[Dict[str, Any]]:
        """Return all tensions (element pairs with conflict/tradeoff/ambiguity)."""
        return list(self._tensions)
