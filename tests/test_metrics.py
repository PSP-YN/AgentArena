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
