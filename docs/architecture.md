# ReCoMo Architecture

## Overview

ReCoMo (Relational Coherence Monitor) is a semantic → relational signal bridge for AI agent reasoning. It turns natural language traces into structured signals and tracks coherence over time.

**Failure mode:** Constraint abandonment in multi-step reasoning — the agent states a constraint (e.g. "minimize cost") and later violates it without detection.

## Pipeline

```
Agent reasoning trace (Inspect AI compatible)
    → Adapter (optional)
    → Claim extractor (LLM)
    → Relational graph
    → Coherence tracker (numeric metrics, trajectory)
    → Drift detector (where + evidence + severity)
    → Report
```

## Schemas

### Input: ReasoningTrace

- **trace_id:** string
- **agent_name:** string
- **task:** string
- **turns:** list of Turn

**Turn:**

- **turn_number:** int (1-based)
- **role:** "agent" | "user" | "system"
- **content:** string
- **metadata:** optional dict

### Extraction output (JSON)

- **goals:** list of {id, content, turn, status}
- **constraints:** list of {id, content, turn, status}
- **entities:** list of {id, content, turn, status}
- **decisions:** list of {id, content, turn, status}
- **assumptions:** list of {id, content, turn, status}

**status:** active | satisfied | violated | abandoned

### Coherence formula

```
overall_coherence = 0.4 * internal_consistency
                  + 0.4 * constraint_integrity
                  + 0.2 * relationship_stability
```

- **internal_consistency:** Do assertions align? (1 − fraction of decisions that violate.)
- **constraint_integrity:** Are constraints respected? (1 − fraction of constraints violated.)
- **relationship_stability:** Stability of supports/contradicts; fewer violations ⇒ higher.

### Drift event

- **turn:** where coherence dropped
- **constraint_id,** **constraint_content**
- **violating_decision_id,** **decision_content**
- **severity:** low | medium | high
- **coherence_drop:** numeric drop at that turn

## Inspect AI adapter

Inspect AI format: `input`, `target`, `messages` (role/content), `metadata`.

We map: `input` → task, `messages` → turns (1-based turn_number), `trace_id` from metadata or hash of input+messages.

## Future directions

- Nova integration: feed relational signals into Relational Memory Synthesizer v2.
- Semantic similarity in checker (LLM-based contradiction detection).
- UDF-style coherence dynamics.
