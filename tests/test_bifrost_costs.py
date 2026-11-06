from app.providers.bifrost import attach_trace_cost, fetch_bifrost_log_cost


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

    def get(self, *args, **kwargs):
        return FakeResponse(self.responses.pop(0))


def test_fetch_bifrost_log_cost(monkeypatch):
    monkeypatch.setenv("BIFROST_LOGS_API_KEY", "logs-test-key")
    monkeypatch.setenv("BIFROST_BASE_URL", "http://bifrost.test")
    FakeClient.responses = [{"logs": [{"id": "req-1", "cost": 0.0042}]}]
    monkeypatch.setattr("app.providers.bifrost.httpx.Client", FakeClient)
    assert fetch_bifrost_log_cost("req-1") == 0.0042


def test_attach_trace_cost_sums_observed_costs(monkeypatch):
    monkeypatch.setenv("BIFROST_LOGS_API_KEY", "logs-test-key")
    monkeypatch.setenv("BIFROST_BASE_URL", "http://bifrost.test")
    FakeClient.responses = [
        {"logs": [{"id": "req-1", "cost": 0.001}]},
        {"logs": [{"id": "req-2", "cost": 0.002}]},
    ]
    monkeypatch.setattr("app.providers.bifrost.httpx.Client", FakeClient)
    result = attach_trace_cost({
        "trace": [
            {"event": "model_step", "request_id": "req-1"},
            {"event": "tool_call", "request_id": "not-a-model-request"},
            {"event": "model_step", "request_id": "req-2"},
        ]
    })
    assert result["cost_usd"] == 0.003
    assert result["cost_status"] == "bifrost_logs_observed"


def test_cost_remains_unknown_without_logs_permission(monkeypatch):
    monkeypatch.delenv("BIFROST_LOGS_API_KEY", raising=False)
    assert fetch_bifrost_log_cost("req-1") is None
