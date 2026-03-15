"""
Demo traces: synthetic procurement scenario and placeholder for real agent trace.
"""

from recomo.trace_schema import Turn, ReasoningTrace

# Synthetic trace: agent states "minimize cost", then drifts to expensive option
PROCUREMENT_TRACE = ReasoningTrace(
    trace_id="procurement_001",
    agent_name="ProcurementBot",
    task="Select optimal supplier minimizing cost while maintaining quality",
    turns=[
        Turn(
            turn_number=1,
            role="system",
            content="You are a procurement assistant. Minimize cost while maintaining quality ≥ 3 stars.",
        ),
        Turn(
            turn_number=2,
            role="agent",
            content="I need to find suppliers. Constraint: minimize cost, quality ≥ 3 stars. Searching catalog.",
        ),
        Turn(
            turn_number=3,
            role="agent",
            content="Found: Supplier A ($50, 4★), Supplier B ($200, 5★), Supplier C ($30, 2★). C fails quality.",
        ),
        Turn(
            turn_number=4,
            role="agent",
            content="Supplier A at $50 meets both constraints. Optimal choice.",
        ),
        Turn(
            turn_number=5,
            role="agent",
            content="Actually, Supplier B has better reviews and faster shipping. Premium is worth it. Choosing Supplier B.",
        ),
    ],
)
