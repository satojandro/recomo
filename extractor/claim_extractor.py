"""
Real LLM-based extraction of relational signals from reasoning traces.

Uses structured output (JSON) for reliability. Client is swappable;
default is OpenAI or OpenRouter based on RECOMO_LLM_PROVIDER and API keys.
"""

import json
import os
from typing import TYPE_CHECKING, Any, Dict, Protocol

from recomo.trace_schema import ReasoningTrace

if TYPE_CHECKING:
    from openai import OpenAI


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


class OpenRouterClient:
    """OpenRouter client. Uses OPENROUTER_API_KEY from environment; API is OpenAI-compatible."""

    def __init__(self, model: str = "openai/gpt-4o-mini"):
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            api_key = os.environ.get("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY environment variable is required for OpenRouter")
            self._client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        return self._client

    def generate(self, prompt: str, *, response_format: Dict[str, str] | None = None) -> str:
        kwargs = {"model": self.model, "messages": [{"role": "user", "content": prompt}]}
        if response_format:
            kwargs["response_format"] = response_format
        response = self._get_client().chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""


# Cached (client, model) for env-based provider so we reuse one connection.
_cached_client: "OpenAI | None" = None
_cached_model: str | None = None


def _get_connection_and_model() -> tuple["OpenAI", str]:
    """Return (OpenAI-compatible client, model) based on RECOMO_LLM_PROVIDER and env keys."""
    global _cached_client, _cached_model
    if _cached_client is not None and _cached_model is not None:
        return _cached_client, _cached_model
    from openai import OpenAI as OpenAIClass

    provider = os.environ.get("RECOMO_LLM_PROVIDER", "").strip().lower()
    openai_key = os.environ.get("OPENAI_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")

    if not provider:
        if openrouter_key and not openai_key:
            provider = "openrouter"
        else:
            provider = "openai"

    model = (os.environ.get("RECOMO_LLM_MODEL") or "").strip()
    if not model:
        model = "gpt-4o-mini" if provider == "openai" else "openai/gpt-4o-mini"

    if provider == "openrouter":
        if not openrouter_key:
            raise ValueError("OPENROUTER_API_KEY required when RECOMO_LLM_PROVIDER=openrouter")
        _cached_client = OpenAIClass(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key)
    else:
        if not openai_key:
            raise ValueError("OPENAI_API_KEY required for real extraction")
        _cached_client = OpenAIClass(api_key=openai_key)

    _cached_model = model
    return _cached_client, _cached_model


class _EnvLLMClient:
    """LLMClient that uses RECOMO_LLM_PROVIDER and RECOMO_LLM_MODEL from environment."""

    def generate(self, prompt: str, *, response_format: Dict[str, str] | None = None) -> str:
        client, model = _get_connection_and_model()
        kwargs = {"model": model, "messages": [{"role": "user", "content": prompt}]}
        if response_format:
            kwargs["response_format"] = response_format
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""


def get_default_llm_client() -> LLMClient:
    """Return an LLMClient configured from RECOMO_LLM_PROVIDER and RECOMO_LLM_MODEL."""
    return _EnvLLMClient()


def get_openai_compatible_client_and_model() -> tuple["OpenAI", str]:
    """Return (OpenAI-compatible client, model) for chat.completions; used by demo and other callers."""
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
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse extraction: {e}", "raw": response}
