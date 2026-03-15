# ReCoMo Architecture

## Overview

ReCoMo implements a **semantic → relational signal bridge** for AI agent evaluation. It transforms natural language reasoning into structured signals that can be tracked for coherence over time.

**Pipeline (high level):**

```
Trace
  ↓
Semantic Extraction (LLM)
  ↓
Relational Graph
  ↓
Coherence Metrics
  ↓
Drift Detection
```

---

## Core Concepts

### Relational Structure

Reasoning is not just text — it's a web of relationships:

- **Goals** relate to **decisions** (pursued / abandoned)
- **Constraints** relate to **decisions** (satisfied / violated)
- **Entities** relate to each other (supports / contradicts / depends_on)
- **Assertions** relate to each other (consistent / contradictory)

When these relationships break, coherence collapses.

### Coherence

Coherence is the degree to which an agent's reasoning maintains internal consistency and respects its own stated constraints.

High coherence: The agent says what it means and does what it says.

Low coherence: The agent contradicts itself, abandons constraints, or makes decisions that conflict with earlier reasoning.

### Drift

Drift is the moment when coherence drops. It's not just "the agent made a mistake" — it's "the agent's reasoning structure became incoherent."

ReCoMo detects drift by tracking coherence turn-by-turn and identifying where it collapses.

---

## Data Structures

### Input: ReasoningTrace

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

### Extraction Output

```python
extraction = {
    "goals": [
        {"id": "goal_1", "content": "...", "turn": 1, "status": "active"}
    ],
    "constraints": [
        {"id": "constraint_cost", "content": "minimize cost", "turn": 1,
         "status": "active", "binding_strength": 0.8}
    ],
    "entities": [
        {"id": "supplier_a", "content": "Supplier A", "turn": 3,
         "attributes": {"cost": 50, "quality": 4}}
    ],
    "decisions": [
        {"id": "decision_1", "content": "Choosing Supplier B", "turn": 5,
         "affects": ["constraint_cost"]}
    ],
    "assumptions": [
        {"id": "assumption_1", "content": "Shipping times are comparable",
         "turn": 3, "status": "active"}
    ]
}
```

### Relational Graph

The implementation uses a `RelationalGraph` that holds nodes (as dicts) and edges. Conceptually:

```python
class Node:
    id: str
    type: str  # "entity" | "goal" | "constraint" | "decision" | "assumption"
    payload: dict

class Edge:
    source: str  # node id
    target: str  # node id
    type: str    # "supports" | "contradicts" | "depends_on" | "satisfies" | "violates"
    weight: float

class RelationalGraph:
    nodes: Dict[str, Node]
    edges: List[Edge]

    def get_constraints() -> List[Node]
    def get_decisions_by_turn(turn: int) -> List[Node]
    def get_contradictions() -> List[Tuple[Node, Node, Edge]]
```

### Coherence Metrics

```python
class CoherenceScore(BaseModel):
    turn: int
    internal_consistency: float  # 0.0 - 1.0
    constraint_integrity: float   # 0.0 - 1.0
    overall_coherence: float      # 0.0 - 1.0

# Formula (documented):
# overall_coherence = 0.5 * internal_consistency + 0.5 * constraint_integrity
#
# (The implementation may add a third term, e.g. relationship_stability, for finer-grained scoring.)
```

### Drift Event

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

## Pipeline

```
1. INPUT
   ReasoningTrace (native) or Inspect AI sample (via adapter)

2. EXTRACTION
   LLM processes trace, outputs structured JSON
   Prompt captures: goals, constraints, entities, decisions, assumptions
   Each element has: id, content, turn, status

3. GRAPH BUILDING
   Extraction → nodes and edges
   Constraints linked to decisions they affect
   Entities linked by relationships

4. COHERENCE COMPUTATION
   For each turn:
     - Check internal consistency (assertion contradictions)
     - Check constraint integrity (violations)
     - Compute overall coherence
   Build trajectory list

5. DRIFT DETECTION
   Identify turns where coherence drops
   Link drop to specific constraint + decision
   Assess severity

6. OUTPUT
   CoherenceReport:
     - extraction summary
     - coherence trajectory
     - drift events with evidence
```

---

## LLM Integration

### Extraction Prompt Design

The extraction prompt should:

1. **Ask for implicit constraints** — not just stated ones
2. **Capture binding strength** — how hard is this constraint?
3. **Identify trade-offs** — where is the agent balancing competing goals?
4. **Track status changes** — when does a constraint become abandoned?

Example prompt structure:

```
Analyze this agent reasoning trace. Extract:

GOALS: What the agent is trying to accomplish
  - Include implicit goals, not just stated ones
  - Note when goals change or get abandoned

CONSTRAINTS: Rules or limitations the agent must respect
  - Include explicit constraints ("minimize cost")
  - Include implicit constraints (quality thresholds, time limits)
  - Rate binding strength: 0.0 (soft preference) to 1.0 (hard constraint)

ENTITIES: Objects, people, systems mentioned
  - Include key attributes (cost, quality, time)

DECISIONS: Choices the agent makes
  - Link to constraints they affect

ASSUMPTIONS: Things taken as given without verification

Output as JSON with the schema: {...}
```

### Structured Output

Use `response_format={"type": "json_object"}` or function calling to ensure parseable output.

---

## Inspect AI Compatibility

Inspect AI traces have this structure:

```python
inspect_sample = {
    "input": "the task prompt",
    "target": "expected output",
    "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
    ],
    "metadata": {...}
}
```

The adapter maps:

| Inspect AI | ReCoMo |
|------------|--------|
| `input` | `task` |
| `messages` | `turns` (with turn_number assigned) |
| `metadata` | `metadata` |
| `id` or hash | `trace_id` |

---

## Future Directions

### Semantic Contradiction Detection

Current: Keyword/heuristic contradiction detection.

Future: Embedding-based semantic similarity to catch contradictions that don't share keywords.

### Multi-Trace Analysis

Compare coherence across multiple runs of the same agent. Identify systematic drift patterns.

### Nova Integration

ReCoMo's extraction output can feed into the Nova relational dynamics framework:

- Full UDF physics (coherence/entropy dynamics)
- Trust-aligned response generation
- Long-term memory integration

### Real-Time Monitoring

Stream agent reasoning through ReCoMo in real-time. Alert on drift as it happens, not post-hoc.

---

## References

- Nova Unified Dynamics Framework (UDF)
- Inspect AI evaluation framework
- Protocol Labs AI Safety Hackathon 2024
