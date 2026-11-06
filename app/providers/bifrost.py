"""Bifrost OpenAI-compatible Chat Completions adapter.

Usage tokens are captured from the response. Cost is optionally fetched from
Bifrost's management Logs API after the benchmark run, using a separate
Logs:View credential. Cost is never guessed.
"""
from __future__ import annotations

import os
import time
import uuid
from typing import Any

import httpx

from app.engine import AgentResponse


class BifrostError(RuntimeError):
    pass


def fetch_bifrost_log_cost(request_id: str, timeout: float = 5.0) -> float | None:
    """Read observed USD cost from Bifrost logs when a Logs:View key is configured."""
    logs_api_key = os.getenv("BIFROST_LOGS_API_KEY", "").strip()
    if not logs_api_key or not request_id:
        return None

    base_url = os.getenv("BIFROST_BASE_URL", "http://localhost:8080").rstrip("/")
    headers = {"Authorization": f"Bearer {logs_api_key}"}
    for attempt in range(3):
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(
                    f"{base_url}/api/logs",
                    headers=headers,
                    params={"request_id": request_id, "limit": 1, "offset": 0},
                )
                response.raise_for_status()
                payload = response.json()
            logs = payload.get("logs") or []
            if logs:
                cost = logs[0].get("cost")
                if isinstance(cost, (int, float)) and not isinstance(cost, bool) and cost >= 0:
                    return float(cost)
                return None
        except (httpx.HTTPError, ValueError, TypeError):
            return None
        if attempt < 2:
            time.sleep(0.15 * (attempt + 1))
    return None


def costs_for_trace(trace: list[dict[str, Any]]) -> list[float | None]:
    """Retrieve costs for every Bifrost model request in an execution trace."""
    request_ids = [
        item.get("request_id")
        for item in trace
        if item.get("event") == "model_step" and isinstance(item.get("request_id"), str)
    ]
    return [fetch_bifrost_log_cost(request_id) for request_id in request_ids]


def attach_trace_cost(result: dict[str, Any]) -> dict[str, Any]:
    """Attach summed observed cost only when every model step has a log cost."""
    trace = result.get("trace") or []
    costs = costs_for_trace(trace)
    if costs and all(cost is not None for cost in costs):
        result["cost_usd"] = round(sum(float(cost) for cost in costs), 8)
        result["cost_status"] = "bifrost_logs_observed"
    else:
        result["cost_usd"] = None
        result["cost_status"] = "unknown_or_logs_unavailable"
    return result


def call_bifrost(prompt: str, model: str, timeout: float = 90.0) -> AgentResponse:
    base_url = os.getenv("BIFROST_BASE_URL", "http://localhost:8080").rstrip("/")
    api_key = os.getenv("BIFROST_API_KEY", "")
    request_id = str(uuid.uuid4())
    headers = {"Content-Type": "application/json", "x-request-id": request_id}
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
    returned_tool_calls = len(message.get("tool_calls") or [])
    return AgentResponse(
        output=content,
        steps=1,
        tool_calls=returned_tool_calls,
        input_tokens=usage.get("prompt_tokens"),
        output_tokens=usage.get("completion_tokens"),
        cost_usd=None,
        trace=[{
            "event": "model_step",
            "request_id": request_id,
            "bifrost_response_id": payload.get("id"),
            "model": model,
            "provider_metrics_available": bool(usage),
            "tool_calls_returned_by_model": returned_tool_calls,
            "note": "Model-emitted tool calls are counted; tools are not executed by this single-call adapter.",
        }],
    )
