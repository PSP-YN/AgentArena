"""Aggregate benchmark results without silently treating missing metrics as zero."""
from __future__ import annotations

from typing import Any


def mean_known(values: list[int | float | None]) -> float | None:
    known = [float(value) for value in values if value is not None]
    return round(sum(known) / len(known), 3) if known else None


def summarize_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    if not runs:
        return {
            "run_count": 0,
            "success_rate": None,
            "mean_score": None,
            "mean_duration_ms": None,
            "mean_steps": None,
            "mean_input_tokens": None,
            "mean_output_tokens": None,
            "total_tool_calls": None,
            "total_cost_usd": None,
            "cost_status": "no_runs",
        }

    count = len(runs)
    costs = [run.get("cost_usd") for run in runs]
    return {
        "run_count": count,
        "success_rate": round(sum(bool(run.get("success")) for run in runs) / count, 3),
        "mean_score": mean_known([run.get("score") for run in runs]),
        "mean_duration_ms": mean_known([run.get("duration_ms") for run in runs]),
        "mean_steps": mean_known([run.get("steps") for run in runs]),
        "mean_input_tokens": mean_known([run.get("input_tokens") for run in runs]),
        "mean_output_tokens": mean_known([run.get("output_tokens") for run in runs]),
        "total_tool_calls": sum(run.get("tool_calls", 0) for run in runs),
        "total_cost_usd": round(sum(float(cost) for cost in costs), 8) if all(cost is not None for cost in costs) else None,
        "cost_status": "complete" if all(cost is not None for cost in costs) else "unknown_or_incomplete",
    }
