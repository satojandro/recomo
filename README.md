# ReCoMo

**Relational Coherence Monitor**

> Detecting reasoning drift in AI agents through relational constraint analysis.

---

## The Problem

AI agents are increasingly autonomous. They plan, reason, and make decisions over multiple steps. But they have a critical failure mode:

**Constraint abandonment.**

An agent begins reasoning under a set of constraints or goals and later violates them — without detection, without correction, without anyone noticing.

```
Step 1: Goal = minimize cost
Step 2: "I need to find the cheapest option..."
Step 5: Chooses expensive solution
```

Most evaluation tools focus on outputs or final task success. ReCoMo focuses on reasoning integrity across the entire trajectory.

---

## The Approach

ReCoMo treats reasoning as a **relational structure**, not just text.

We build a semantic bridge:

```
Agent reasoning trace
        ↓
    Extraction
        ↓
  Relational graph
        ↓
 Coherence metrics
        ↓
   Drift detection
```

ReCoMo treats reasoning as a trajectory rather than a single decision. By computing coherence turn-by-turn, it can detect when an agent's reasoning begins aligned but gradually drifts away from its own constraints.

**What we extract:**

- Goals — what the agent is trying to accomplish
- Constraints — rules and limitations the agent must respect
- Entities — objects, people, systems mentioned
- Decisions — choices the agent makes
- Assumptions — things taken as given

**What we compute:**

- Internal consistency — do assertions align with each other?
- Constraint integrity — are stated constraints respected?
- Overall coherence — weighted combination, tracked turn-by-turn

**What we detect:**

- WHERE coherence drops
- WHICH constraint was violated
- WHAT decision caused it
- HOW SEVERE the drift is

---

## Why It Matters

Modern AI safety tools focus on outputs. ReCoMo monitors reasoning structure.

This is especially critical for decentralized systems. When AI agents interact with protocols, smart contracts, and distributed infrastructure, there's no central authority to catch misalignment. The agent itself must be verifiable.

ReCoMo is trust infrastructure for agent constraint consistency — especially critical in decentralized systems where autonomous agents interact with protocols and smart contracts without centralized oversight.

---

## Quick Start

```bash
# Clone and install
git clone https://github.com/your-org/recomo.git
cd recomo
pip install -r requirements.txt

# Set your OpenRouter API key
export OPENROUTER_API_KEY=your-key-here

# Run the demo (from project root)
python run_demo.py                    # synthetic trace (default)
python run_demo.py real               # real agent chain (may drift)
python run_demo.py path/to/trace.json # Inspect AI trace file
```

Or install the package and run from anywhere:

```bash
pip install -e .
python -m recomo.demo                 # synthetic
python -m recomo.demo real            # real agent chain
```

---

## Demo Output

```
============================================================
ReCoMo — Relational Coherence Monitor
============================================================

[INPUT] Procurement Trace (5 turns)
Task: Select optimal supplier minimizing cost while maintaining quality

[EXTRACTION] Signals detected:
  Goals: 1
  Constraints: 2 (minimize_cost, quality_≥_3_stars)
  Entities: 3 (Supplier A, B, C)
  Decisions: 2

[COHERENCE] Trajectory:
  Turn 1: 1.00
  Turn 2: 1.00
  Turn 3: 1.00
  Turn 4: 1.00
  Turn 5: 0.60  ← DROP DETECTED

[DRIFT ALERT] Constraint abandonment
  Turn: 5
  Constraint: "minimize cost"
  Violating decision: "Choosing Supplier B ($200)"
  Severity: HIGH
  Evidence: Agent chose $200 option when $50 option satisfied all constraints

============================================================
```

---

## Architecture

See [docs/architecture.md](docs/architecture.md) for full schema and design details.

---

## Project layout

The project folder is the package (no nested `recomo/recomo/`):

```
recomo/
├── __init__.py
├── trace_schema.py       # Turn, ReasoningTrace
├── extractor/            # LLM extraction (prompts, claim_extractor)
├── graph/                # Relational graph
├── checker/              # Coherence tracker, drift detector
├── adapters/             # Inspect AI → ReasoningTrace
├── demo/                 # Traces, real agent chain, run_demo
├── run_demo.py           # Run from project root without installing
├── demo.ipynb
├── docs/architecture.md
└── README.md
```

---

## Integration

ReCoMo accepts traces in **Inspect AI format** — the recommended evaluation tooling for this track.

```python
from recomo.adapters.inspect_ai import inspect_trace_to_reasoning_trace
from recomo.extractor import ClaimExtractor
from recomo.graph import RelationalGraph
from recomo.checker import CoherenceTracker, DriftDetector

# Convert Inspect AI trace
trace = inspect_trace_to_reasoning_trace(inspect_sample)

# Run pipeline
extractor = ClaimExtractor()
extraction = extractor.extract(trace)
graph = RelationalGraph()
graph.load_extraction(extraction)
tracker = CoherenceTracker(graph)
tracker.compute_trajectory()
detector = DriftDetector(graph, tracker)
drifts = detector.detect()

# Report: extraction, tracker.get_trajectory(), drifts
```

---

## Roadmap

- Semantic similarity for contradiction detection
- Multi-trace coherence comparison
- Integration with Nova relational dynamics framework
- Real-time monitoring mode
- Real-time monitoring for autonomous agents.

---

## License

MIT

---

## Acknowledgments

```
Note: ReCoMo is an independent prototype created for the Protocol Labs AI Safety Hackathon. It is part of a broader research effort on relational intelligence and agent reasoning systems. 

The broader Nova and Unified Dynamics Framework (UDF) research codebase is not included in this repository AND NOT LICENSED UNDER MIT
```

