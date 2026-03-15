"""
Scenario schema for multi-scenario simulation.

One scenario = one reproducible trace: task, system prompt (constraints),
and a list of user messages. The simulator runs agent (LLM) after each user
message and builds a ReasoningTrace.
"""

from typing import List

from pydantic import BaseModel, Field


class Scenario(BaseModel):
    """Environment-driven scenario: id, task, system prompt, user message script."""

    id: str = Field(..., description="Unique scenario identifier (used as trace_id)")
    task: str = Field(..., description="Task description")
    system_prompt: str = Field(
        ...,
        description="System prompt for the agent (constraints, role)",
    )
    user_messages: List[str] = Field(
        default_factory=list,
        description="Ordered list of user messages; agent responds after each.",
    )
