# ReCoMo Architecture

ReCoMo monitors the **structural evolution of reasoning**.

Instead of evaluating final answers, it tracks the **trajectory of reasoning relationships**.

---

# Pipeline

```
trace
  ↓
extraction
  ↓
relational graph
  ↓
coherence metrics
  ↓
drift detection
```

---

# Reasoning Trace

A trace is a sequence of turns:

```
Turn {
  turn_number
  role
  content
}
```

Example flow:

```
system → user → assistant → user → assistant
```

```python
class Turn(BaseModel):
    turn_number: int
    role: str  # "agent" | "user" | "system"
    content: str
    metadata: Optional[dict] = None

class ReasoningTrace(BaseModel):
    trace_id: str
    agent_name: str
    task: str
    turns: List[Turn]
```

---

# Extraction

An LLM extracts reasoning structures from each turn.

**Entities:**

- Goals
- Constraints
- Decisions
- Assumptions

These become graph nodes. Each element has: `id`, `content`, `turn`, `status` (active | satisfied | violated | abandoned).

---

# Relational Graph

The reasoning graph models dependencies.

Example:

```
Goal
  ↑
Decision
  ↑
Assumption
```

Conflicts or violations create edges like:

```
decision ──violates──> constraint
```

```python
class Node:
    id: str
    type: str  # "entity" | "goal" | "constraint" | "decision" | "assumption"
    payload: dict

class Edge:
    source: str
    target: str
    type: str  # "supports" | "violates" | "depends_on" | "conflicts_with" | ...
    weight: float
```

---

# Coherence Metrics

From the graph we compute:

### Overall Coherence

Global structural consistency (weighted combination of sub-metrics).

### Internal Consistency

Compatibility of decisions — do assertions align with each other?

### Constraint Integrity

Whether decisions violate stated constraints.

### Relationship Stability

How stable the reasoning graph is over time.

```python
class CoherenceScore(BaseModel):
    turn: int
    internal_consistency: float   # 0.0 - 1.0
    constraint_integrity: float   # 0.0 - 1.0
    overall_coherence: float      # 0.0 - 1.0
```

---

# Drift Detection

ReCoMo detects several failure modes:

| Drift Type | Description |
|------------|-------------|
| Constraint Drift | constraints violated |
| Goal Drift | goals abandoned |
| Decision Conflict | incompatible decisions |
| Assumption Drift | assumptions invalidated |
| Instability | rapid structural change |

```python
class DriftEvent(BaseModel):
    turn: int
    constraint_id: str
    constraint_content: str
    violating_decision_id: str
    decision_content: str
    severity: str  # "low" | "medium" | "high"
    coherence_drop: float
```

---

# Interfaces

ReCoMo exposes three interfaces:

| Interface | Purpose |
|-----------|---------|
| TUI | live reasoning monitoring |
| Replay | offline trace analysis |
| Graph Viz | visual reasoning graph |

---

# Design Principles

ReCoMo focuses on **trajectory evaluation**.

Key ideas:

1. **Reasoning is a structure** — not just text, but a web of goals, constraints, decisions, and assumptions.
2. **Structures evolve over time** — coherence is computed turn-by-turn.
3. **Failures appear as structural drift** — when relationships break, coherence collapses.

---

# Inspect AI Compatibility

ReCoMo accepts traces in Inspect AI format via adapter:

| Inspect AI | ReCoMo |
|------------|--------|
| `input` | `task` |
| `messages` | `turns` |
| `metadata` | `metadata` |

---

# Future Directions

- Semantic similarity for contradiction detection (embedding-based)
- Multi-trace coherence comparison
- Integration with Nova relational dynamics framework
- Real-time streaming monitoring
