# ReCoMo

### Relational Coherence Monitor

ReCoMo observes **how an AI reasons**, not just what it outputs.

Most evaluation tools score the **final answer**.  
ReCoMo monitors the **reasoning trajectory** — the evolving structure of:

- goals
- constraints
- decisions
- assumptions

When those relationships break, ReCoMo detects **drift**.

---

# The Failure Mode We Target

AI systems frequently **violate their own reasoning**.

Example:

1. The model states a constraint
2. Later reasoning ignores or contradicts it
3. The final answer still looks reasonable

Traditional evaluations **miss this failure**.

ReCoMo detects it in real time by monitoring the **structure of reasoning**.

---

# What ReCoMo Does

ReCoMo transforms a reasoning trace into a **relational graph**.

**Nodes:**

- Goals
- Constraints
- Decisions
- Assumptions

**Edges:**

- Supports
- Violates
- Depends on
- Conflicts with

From this graph we compute **coherence metrics**:

| Metric | Meaning |
|--------|---------|
| Overall Coherence | structural consistency of reasoning |
| Internal Consistency | logical compatibility between decisions |
| Constraint Integrity | whether stated constraints are respected |
| Relationship Stability | structural stability of the reasoning graph |

When these degrade, ReCoMo raises **drift alerts**.

---

# System Overview

```
conversation
      ↓
reasoning extraction
      ↓
relational graph
      ↓
coherence metrics
      ↓
drift detection
```

ReCoMo can run:

- **Replay mode** — analyze an existing trace
- **Interactive mode** — monitor reasoning live

---

# Quick Start

```bash
# Clone and install
git clone https://github.com/your-org/recomo.git
cd recomo
pip install -r requirements.txt
pip install -e .

# Set your OpenRouter API key
export OPENROUTER_API_KEY=your-key-here
```

---

# Demo Interfaces

ReCoMo includes two interfaces:

### Terminal UI (TUI)

```bash
python -m recomo.tui
```

Features:

- live conversation
- coherence metrics
- drift alerts

With no argument, the built-in synthetic trace loads so you can try it immediately. Pass a trace path to replay:

```bash
python -m recomo.tui path/to/trace.json
```

### Graph Visualization

```bash
python -m recomo.viz.export_demo
cd viz
python -m http.server 8080
```

Open: **http://localhost:8080**

Shows:

- reasoning graph
- trajectory over time
- drift events

---

# Deterministic Demo Scenario (Triggers Drift)

Run a scenario where the agent is nudged to violate its own constraints:

```bash
python -m recomo.demo.run_demo --simulate demo/scenarios/procurement_nudge.json
```

The agent states a budget constraint ($100) but is nudged to reconsider. ReCoMo detects when the agent abandons the constraint.

---

# Example Drift Scenario

**User prompt:**

> Plan a trip to New York under $1000.

**Agent states constraint:**

> Constraint: total budget must remain under $1000.

**Later reasoning:**

> Hotel: $1200  
> Flights: $400  
> Total: $1600

Final answer still looks coherent — but the constraint is violated.

ReCoMo detects this **structural failure** immediately.

---

# Why This Matters

As AI systems become autonomous, we need tools that detect **reasoning failures before deployment**.

ReCoMo provides **reasoning observability**:

- structural evaluation
- trajectory monitoring
- drift detection

instead of just scoring outputs.

---

# Integration

ReCoMo accepts traces in **Inspect AI format**:

```python
from recomo.adapters.inspect_ai import inspect_trace_to_reasoning_trace
from recomo.extractor import ClaimExtractor
from recomo.graph import RelationalGraph
from recomo.checker import CoherenceTracker, DriftDetector

trace = inspect_trace_to_reasoning_trace(inspect_sample)
extractor = ClaimExtractor()
extraction = extractor.extract(trace)
graph = RelationalGraph()
graph.load_extraction(extraction)
tracker = CoherenceTracker(graph)
tracker.compute_trajectory()
detector = DriftDetector(graph, tracker)
drifts = detector.detect()
```

---

# Project Layout

```
recomo/
├── trace_schema.py       # Turn, ReasoningTrace
├── extractor/            # LLM extraction
├── graph/                # Relational graph
├── checker/              # Coherence tracker, drift detector
├── adapters/             # Inspect AI → ReasoningTrace
├── simulator/            # Scenario simulation
├── demo/                 # Traces, run_demo, scenarios
├── viz/                  # Graph visualization
├── tui/                  # Terminal UI
└── docs/architecture.md
```

---

# Future Work

- incremental extraction
- multi-agent reasoning graphs
- adversarial reasoning evaluation
- integration with Inspect AI

---

# License

MIT

---

# Acknowledgments

ReCoMo is an independent prototype created for the Protocol Labs AI Safety Hackathon. It is part of a broader research effort on relational intelligence and agent reasoning systems. The broader Nova and Unified Dynamics Framework (UDF) research codebase is not included in this repository and is not licensed under MIT.
