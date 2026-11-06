"""Bifrost OpenAI-compatible Chat Completions adapter.

Bifrost usage metrics are captured when returned by the gateway. Cost remains
unknown unless a trusted cost source is integrated; it is never guessed here.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

from app.engine import AgentResponse


class BifrostError(RuntimeError):
    pass


def call_bifrost(prompt: str, model: str, timeout: float = 90.0) -> AgentResponse:
    base_url = os.getenv("BIFROST_BASE_URL", "http://localhost:8080").rstrip("/")
    api_key = os.getenv("BIFROST_API_KEY", "")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{base_url}/v1/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                },
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
    except httpx.HTTPError as exc:
        raise BifrostError(f"Bifrost request failed: {type(exc).__name__}") from exc

    choices = payload.get("choices") or []
    if not choices:
        raise BifrostError("Bifrost response contained no choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise BifrostError("Bifrost response did not contain text content")

    usage = payload.get("usage") or {}
    return AgentResponse(
        output=content,
        tool_calls=len(message.get("tool_calls") or []),
        input_tokens=usage.get("prompt_tokens"),
        output_tokens=usage.get("completion_tokens"),
        cost_usd=None,
        trace=[{
            "event": "bifrost_chat_completion",
            "model": model,
            "request_id": payload.get("id"),
            "provider_metrics_available": bool(usage),
        }],
    )
