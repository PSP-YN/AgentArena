from app.engine import AgentResponse, BenchmarkTask, run_task, score_output


def test_normalized_exact_match():
    assert score_output("Hello World", " hello   world ") == 1.0
    assert score_output("Hello", "Goodbye") == 0.0


def test_contains_scorer():
    assert score_output("world", "Hello world!", "contains") == 1.0


def test_run_task_keeps_missing_cost_unknown():
    task = BenchmarkTask("t1", "prompt", "answer")
    result = run_task(task, "test-agent", lambda _: AgentResponse("answer"))
    assert result.success is True
    assert result.score == 1.0
    assert result.cost_usd is None
    assert result.input_tokens is None
    assert result.output_tokens is None
    assert result.duration_ms >= 0
