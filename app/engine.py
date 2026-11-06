"""Core AgentArena benchmark engine.

This module deliberately separates observed agent metrics from estimated values.
No token/cost numbers are invented when the agent adapter does not provide them.
"""
from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class AgentResponse:
    output: str
    tool_calls: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    trace: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class BenchmarkTask:
    task_id: str
    prompt: str
    expected_output: str
    scorer: str = "normalized_exact_match"


@dataclass
class BenchmarkResult:
    run_id: str
    task_id: str
    agent_name: str
    output: str
    success: bool
    score: float
    duration_ms: float
    tool_calls: int
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None
    trace: list[dict[str, Any]]


Agent = Callable[[str], AgentResponse]


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().casefold())


def score_output(expected: str, actual: str, scorer: str = "normalized_exact_match") -> float:
    if scorer == "normalized_exact_match":
        return 1.0 if normalize(expected) == normalize(actual) else 0.0
    if scorer == "contains":
        return 1.0 if normalize(expected) in normalize(actual) else 0.0
    raise ValueError(f"Unsupported scorer: {scorer}")


def run_task(task: BenchmarkTask, agent_name: str, agent: Agent) -> BenchmarkResult:
    started = time.perf_counter()
    response = agent(task.prompt)
    duration_ms = (time.perf_counter() - started) * 1000
    score = score_output(task.expected_output, response.output, task.scorer)
    return BenchmarkResult(
        run_id=str(uuid.uuid4()),
        task_id=task.task_id,
        agent_name=agent_name,
        output=response.output,
        success=score >= 1.0,
        score=score,
        duration_ms=round(duration_ms, 3),
        tool_calls=response.tool_calls,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        cost_usd=response.cost_usd,
        trace=response.trace,
    )
