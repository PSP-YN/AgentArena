"""Aggregate benchmark results without silently treating missing metrics as zero."""
from __future__ import annotations

import math
import statistics
from typing import Any


def known(values: list[int | float | None]) -> list[float]:
    return [float(value) for value in values if value is not None]


def mean_known(values: list[int | float | None]) -> float | None:
    items = known(values)
    return round(statistics.fmean(items), 3) if items else None


def percentile(values: list[int | float | None], quantile: float) -> float | None:
    items = sorted(known(values))
    if not items:
        return None
    if len(items) == 1:
        return round(items[0], 3)
    position = (len(items) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    result = items[lower] + (items[upper] - items[lower]) * (position - lower)
    return round(result, 3)


def summarize_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    if not runs:
        return {
            "run_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "success_rate": None,
            "mean_score": None,
            "mean_duration_ms": None,
            "median_duration_ms": None,
            "p95_duration_ms": None,
            "latency_stddev_ms": None,
            "mean_steps": None,
            "mean_input_tokens": None,
            "mean_output_tokens": None,
            "total_tool_calls": 0,
            "total_cost_usd": None,
            "cost_status": "no_runs",
        }

    count = len(runs)
    durations = known([run.get("duration_ms") for run in runs])
    costs = [run.get("cost_usd") for run in runs]
    successes = sum(bool(run.get("success")) for run in runs)
    return {
        "run_count": count,
        "success_count": successes,
        "failure_count": count - successes,
        "success_rate": round(successes / count, 3),
        "mean_score": mean_known([run.get("score") for run in runs]),
        "mean_duration_ms": mean_known([run.get("duration_ms") for run in runs]),
        "median_duration_ms": percentile([run.get("duration_ms") for run in runs], 0.5),
        "p95_duration_ms": percentile([run.get("duration_ms") for run in runs], 0.95),
        "latency_stddev_ms": round(statistics.stdev(durations), 3) if len(durations) > 1 else (0.0 if durations else None),
        "mean_steps": mean_known([run.get("steps") for run in runs]),
        "mean_input_tokens": mean_known([run.get("input_tokens") for run in runs]),
        "mean_output_tokens": mean_known([run.get("output_tokens") for run in runs]),
        "total_tool_calls": sum(int(run.get("tool_calls") or 0) for run in runs),
        "total_cost_usd": round(sum(float(cost) for cost in costs), 8) if all(cost is not None for cost in costs) else None,
        "cost_status": "complete" if all(cost is not None for cost in costs) else "unknown_or_incomplete",
    }
