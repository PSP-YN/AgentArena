import json

from app.agents.bifrost_tool_agent import run_bifrost_tool_agent


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    responses = []

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, *args, **kwargs):
        return FakeResponse(self.responses.pop(0))


def test_tool_loop_executes_calculator_and_aggregates_usage(monkeypatch):
    tool_call = {
        "id": "call-1",
        "type": "function",
        "function": {"name": "calculator", "arguments": json.dumps({"expression": "1 + 1"})},
    }
    FakeClient.responses = [
        {"id": "step-1", "choices": [{"message": {"content": None, "tool_calls": [tool_call]}}], "usage": {"prompt_tokens": 10, "completion_tokens": 3}},
        {"id": "step-2", "choices": [{"message": {"content": "2", "tool_calls": []}}], "usage": {"prompt_tokens": 20, "completion_tokens": 1}},
    ]
    monkeypatch.setattr("app.agents.bifrost_tool_agent.httpx.Client", FakeClient)

    result = run_bifrost_tool_agent("Calculate 1 + 1", "test/model")
    assert result.output == "2"
    assert result.steps == 2
    assert result.tool_calls == 1
    assert result.input_tokens == 30
    assert result.output_tokens == 4
    assert any(item["event"] == "tool_call" for item in result.trace)
