"""
Agent adapter: get the next agent response given a list of messages.

Used by interactive mode and can be shared with the simulator.
Messages are in OpenAI/OpenRouter format: [{"role": "system"|"user"|"assistant", "content": "..."}].
"""

from typing import List


def get_next_agent_response(
    messages: List[dict],
    model: str | None = None,
) -> str:
    """
    Send messages to the LLM and return the assistant reply.
    messages: list of {"role": "system"|"user"|"assistant", "content": "..."}.
    Does not mutate messages; the caller should append the returned reply.
    """
    from recomo.extractor.claim_extractor import get_llm_client_and_model

    # #region agent log
    try:
        _logpath = __import__("pathlib").Path(__file__).resolve().parent.parent / ".cursor" / "debug-66406c.log"
        _roles = [m.get("role") for m in messages]
        _last = messages[-1] if messages else {}
        _logpath.parent.mkdir(parents=True, exist_ok=True)
        open(_logpath, "a").write(
            __import__("json").dumps({"sessionId": "66406c", "hypothesisId": "H1,H2,H4", "location": "agent_adapter.py:entry", "message": "before API call", "data": {"n_messages": len(messages), "roles": _roles, "last_role": _last.get("role"), "last_content_len": len((_last.get("content")) or "")}, "timestamp": __import__("time").time() * 1000}) + "\n"
        )
    except Exception:
        pass
    # #endregion

    client, default_model = get_llm_client_and_model()
    effective_model = model if model is not None else default_model
    response = client.chat.completions.create(model=effective_model, messages=messages)

    # #region agent log
    try:
        _logpath = __import__("pathlib").Path(__file__).resolve().parent.parent / ".cursor" / "debug-66406c.log"
        _c = response.choices[0].message.content if response.choices else None
        _typ = type(_c).__name__
        _len = len(_c) if _c else 0
        _preview = repr((_c or "")[:200]) if _c else ""
        if isinstance(_c, list):
            _typ = "list"
            _len = len(_c)
            _preview = repr(_c)[:300]
        _logpath.parent.mkdir(parents=True, exist_ok=True)
        open(_logpath, "a").write(
            __import__("json").dumps({"sessionId": "66406c", "hypothesisId": "H1,H4", "location": "agent_adapter.py:after API", "message": "API response content", "data": {"content_type": _typ, "content_len": _len, "content_preview": _preview, "n_choices": len(response.choices)}, "timestamp": __import__("time").time() * 1000}) + "\n"
        )
    except Exception:
        pass
    # #endregion

    raw = response.choices[0].message.content
    # Some models/APIs return content as a list of parts (e.g. [{"type":"text","text":"..."}])
    if isinstance(raw, list):
        parts = [p.get("text", "") for p in raw if isinstance(p, dict) and p.get("type") == "text"]
        return " ".join(parts).strip() if parts else ""
    return raw or ""
