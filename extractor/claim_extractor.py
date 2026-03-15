"""
Real LLM-based extraction of relational signals from reasoning traces.

Uses structured output (JSON) for reliability. Client is swappable;
default is OpenAI with API key from environment.
"""

import json
import os
from typing import Any, Dict, Protocol

from recomo.trace_schema import ReasoningTrace


class LLMClient(Protocol):
    """Protocol for an LLM client used by the extractor."""

    def generate(self, prompt: str, *, response_format: Dict[str, str] | None = None) -> str:
        """Return raw model response. If response_format requests JSON, response should be parseable JSON."""
        ...


class OpenAIClient:
    """OpenAI client. Uses OPENAI_API_KEY from environment."""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required for real extraction")
            self._client = OpenAI(api_key=api_key)
        return self._client

    def generate(self, prompt: str, *, response_format: Dict[str, str] | None = None) -> str:
        kwargs = {"model": self.model, "messages": [{"role": "user", "content": prompt}]}
        if response_format:
            kwargs["response_format"] = response_format
        response = self._get_client().chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""


class ClaimExtractor:
    """Extracts goals, constraints, entities, decisions, assumptions from a reasoning trace via LLM."""

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client if llm_client is not None else OpenAIClient()

    def format_trace(self, trace: ReasoningTrace) -> str:
        """Convert ReasoningTrace to text for LLM input."""
        lines = []
        for turn in trace.turns:
            lines.append(f"[Turn {turn.turn_number}] [{turn.role}]: {turn.content}")
        return "\n".join(lines)

    def extract(self, trace: ReasoningTrace) -> Dict[str, Any]:
        """Extract relational signals from trace. Returns dict with goals, constraints, entities, decisions, assumptions."""
        trace_text = self.format_trace(trace)
        from recomo.extractor.prompts import EXTRACTION_PROMPT
        prompt = EXTRACTION_PROMPT.format(trace_text=trace_text)
        response = self.llm.generate(prompt, response_format={"type": "json_object"})
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse extraction: {e}", "raw": response}
