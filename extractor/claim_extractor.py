"""
Real LLM-based extraction of relational signals from reasoning traces.

Uses structured output (JSON) for reliability. Uses OpenRouter for chat completions.
"""

import json
import os
import re
from typing import TYPE_CHECKING, Any, Dict, Protocol

from recomo.trace_schema import ReasoningTrace

if TYPE_CHECKING:
    from openai import OpenAI as _ChatClient


def _extract_json_from_response(response: str) -> str | None:
    """Try to extract a JSON object from response that may be wrapped in prose or markdown."""
    if not response or not response.strip():
        return None
    text = response.strip()
    # Try markdown code block first: ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        candidate = match.group(1).strip()
        if candidate.startswith("{"):
            return candidate
    # Fallback: find balanced { ... }
    start = text.find("{")
    if start >= 0:
        depth = 0
        for i, c in enumerate(text[start:], start):
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    return None


class LLMClient(Protocol):
    """Protocol for an LLM client used by the extractor."""

    def generate(self, prompt: str, *, response_format: Dict[str, str] | None = None) -> str:
        """Return raw model response. If response_format requests JSON, response should be parseable JSON."""
        ...


class OpenRouterClient:
    """OpenRouter client. Uses OPENROUTER_API_KEY from environment."""

    def __init__(self, model: str = "openai/gpt-4o-mini"):
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            api_key = os.environ.get("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY environment variable is required")
            self._client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key, timeout=120.0)
        return self._client

    def generate(self, prompt: str, *, response_format: Dict[str, str] | None = None) -> str:
        kwargs = {"model": self.model, "messages": [{"role": "user", "content": prompt}]}
        if response_format:
            kwargs["response_format"] = response_format
        response = self._get_client().chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""


# Cached (client, model) for env-based config so we reuse one connection.
_cached_client: "_ChatClient | None" = None
_cached_model: str | None = None


def _get_connection_and_model() -> tuple["_ChatClient", str]:
    """Return (OpenRouter client, model) from OPENROUTER_API_KEY and RECOMO_LLM_MODEL."""
    global _cached_client, _cached_model
    if _cached_client is not None and _cached_model is not None:
        return _cached_client, _cached_model
    from openai import OpenAI
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is required")
    model = (os.environ.get("RECOMO_LLM_MODEL") or "").strip() or "openai/gpt-4o-mini"
    _cached_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key, timeout=120.0)
    _cached_model = model
    return _cached_client, _cached_model


class _EnvLLMClient:
    """LLMClient that uses RECOMO_LLM_MODEL from environment with OpenRouter."""

    def generate(self, prompt: str, *, response_format: Dict[str, str] | None = None) -> str:
        client, model = _get_connection_and_model()
        kwargs = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        if response_format:
            kwargs["response_format"] = response_format
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""


def get_default_llm_client() -> LLMClient:
    """Return an LLMClient configured from RECOMO_LLM_MODEL (OpenRouter)."""
    return _EnvLLMClient()


def get_llm_client_and_model() -> tuple["_ChatClient", str]:
    """Return (OpenRouter client, model) for chat.completions; used by demo and other callers."""
    return _get_connection_and_model()


class ClaimExtractor:
    """Extracts goals, constraints, entities, decisions, assumptions from a reasoning trace via LLM."""

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client if llm_client is not None else get_default_llm_client()

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
        # Try direct parse first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        # Fallback: extract JSON from markdown/prose-wrapped response
        extracted = _extract_json_from_response(response)
        if extracted:
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                pass
        return {"error": "Failed to parse extraction: LLM did not return valid JSON", "raw": response[:500]}
