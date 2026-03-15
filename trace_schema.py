"""
Input contract for agent reasoning traces.

Compatible with Inspect AI format: their `messages` (role/content) map to
our Turn list; `input` maps to task; trace_id can come from metadata or hash.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class Turn(BaseModel):
    """A single turn in an agent reasoning trace."""

    turn_number: int = Field(..., description="1-based turn index")
    role: str = Field(..., description="'agent' | 'user' | 'system'")
    content: str = Field(..., description="Raw text of the turn")
    metadata: Optional[dict] = Field(default=None, description="Optional turn-level metadata")


class ReasoningTrace(BaseModel):
    """Full reasoning trace: task plus ordered turns."""

    trace_id: str = Field(..., description="Unique identifier for this trace")
    agent_name: str = Field(..., description="Name or id of the agent")
    task: str = Field(..., description="Task or prompt the agent is addressing")
    turns: List[Turn] = Field(default_factory=list, description="Ordered turns (system/user/agent)")
