from app.metrics import summarize_runs


def test_summary_keeps_cost_unknown_if_any_run_missing_cost():
    summary = summarize_runs([
        {"success": True, "score": 1.0, "duration_ms": 100, "tool_calls": 1, "input_tokens": 10, "output_tokens": 5, "cost_usd": None},
        {"success": False, "score": 0.0, "duration_ms": 200, "tool_calls": 0, "input_tokens": None, "output_tokens": None, "cost_usd": None},
    ])
    assert summary["success_rate"] == 0.5
    assert summary["mean_duration_ms"] == 150
    assert summary["mean_input_tokens"] == 10
    assert summary["total_tool_calls"] == 1
    assert summary["total_cost_usd"] is None
    assert summary["cost_status"] == "unknown_or_incomplete"


def test_summary_reports_known_total_cost():
    summary = summarize_runs([
        {"success": True, "score": 1.0, "duration_ms": 10, "tool_calls": 0, "input_tokens": 1, "output_tokens": 2, "cost_usd": 0.01},
        {"success": True, "score": 1.0, "duration_ms": 20, "tool_calls": 0, "input_tokens": 3, "output_tokens": 4, "cost_usd": 0.02},
    ])
    assert summary["total_cost_usd"] == 0.03
    assert summary["cost_status"] == "complete"


def test_summary_reports_reliability_and_latency_distribution():
    summary = summarize_runs([
        {"success": True, "score": 1.0, "duration_ms": 100, "steps": 2, "tool_calls": 1, "cost_usd": 0.01},
        {"success": False, "score": 0.0, "duration_ms": 200, "steps": 3, "tool_calls": 2, "cost_usd": 0.02},
        {"success": True, "score": 1.0, "duration_ms": 300, "steps": 2, "tool_calls": 0, "cost_usd": None},
    ])
    assert summary["success_count"] == 2
    assert summary["failure_count"] == 1
    assert summary["success_rate"] == 0.667
    assert summary["median_duration_ms"] == 200
    assert summary["p95_duration_ms"] == 290
    assert summary["total_tool_calls"] == 3
    assert summary["total_cost_usd"] is None


def test_empty_summary_keeps_unknown_values_null():
    summary = summarize_runs([])
    assert summary["run_count"] == 0
    assert summary["success_rate"] is None
    assert summary["total_cost_usd"] is None
