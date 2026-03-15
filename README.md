# ReCoMo — Relational Coherence Monitor

**Detecting reasoning drift in AI agents through relational constraint analysis.**

ReCoMo is a semantic → relational signal bridge: it turns an agent’s natural language reasoning into structured signals (goals, constraints, entities, decisions) and tracks coherence over time. When the agent abandons a stated constraint — e.g. “minimize cost” then “choose the expensive option” — ReCoMo detects where it happened and reports evidence.

## Failure mode

**Constraint abandonment in multi-step reasoning.** The agent states a constraint or goal and later violates it without detection. ReCoMo identifies the turn, the constraint, and the violating decision, and computes a coherence trajectory (not just a boolean alert).

## Approach

1. **Extract** — LLM extracts goals, constraints, entities, decisions, and assumptions from the trace (structured JSON).
2. **Graph** — In-memory relational graph with constraints, decisions, and contradiction edges.
3. **Coherence** — Numeric scores per turn: internal consistency, constraint integrity, relationship stability. Overall coherence = `0.4×IC + 0.4×CI + 0.2×RS`.
4. **Drift** — Detect where coherence drops; report turn, constraint, decision, severity, and coherence drop.

Inspect AI traces are supported via an adapter, so ReCoMo fits into their evaluation ecosystem.

## Why Protocol Labs should care

As AI agents interact with decentralized systems, we need infrastructure to verify that their behavior stays consistent with declared constraints. ReCoMo is a step toward that trust infrastructure.

## Setup

```bash
cd recomo
pip install -r requirements.txt
export OPENAI_API_KEY=your_key   # required for extraction and real agent demo
```

## Run the demo

From the project root (`recomo/`):

```bash
python run_demo.py                    # synthetic trace (default)
python run_demo.py real               # real agent chain (may drift)
python run_demo.py path/to/trace.json # Inspect AI trace file
```

Or install the package and run from anywhere:

```bash
pip install -e .
python -m recomo.demo                 # synthetic
python -m recomo.demo real
```

Requires `OPENAI_API_KEY` for extraction and for the real agent chain.

The report prints extracted signals, coherence trajectory, and any drift alerts with evidence.

## Project layout

The project folder is the package (no nested `recomo/recomo/`):

```
recomo/
├── __init__.py
├── trace_schema.py       # Turn, ReasoningTrace
├── extractor/             # LLM extraction (prompts, claim_extractor)
├── graph/                 # Relational graph
├── checker/               # Coherence tracker, drift detector
├── adapters/              # Inspect AI → ReasoningTrace
├── demo/                  # Traces, real agent chain, run_demo
├── run_demo.py            # Run from project root without installing
├── demo.ipynb
├── docs/architecture.md
└── README.md
```

## License

MIT.
