from fastapi.testclient import TestClient

from app.main import app
from app.providers.bifrost import BifrostError

client = TestClient(app)


def test_task_catalog_has_resilience_cases():
    response = client.get("/api/v1/tasks")
    assert response.status_code == 200
    task_ids = {task["task_id"] for task in response.json()["tasks"]}
    assert "calculator-retry-19x23" in task_ids
    assert "untrusted-document-injection" in task_ids
    assert "provider-outage" in task_ids


def test_simulated_provider_outage_is_recorded_as_failed_trial(monkeypatch):
    def outage(*args, **kwargs):
        raise BifrostError("Simulated provider outage injected by AgentArena")

    monkeypatch.setattr("app.main.run_bifrost_tool_agent", outage)
    response = client.post("/api/v1/bifrost-benchmarks", json={
        "task_id": "outage-test",
        "prompt": "Return Paris",
        "expected_output": "Paris",
        "models": ["provider/test"],
        "repeats": 1,
        "fault_mode": "provider_outage",
    })
    assert response.status_code == 200
    model = response.json()["models"][0]
    assert model["runs"][0]["success"] is False
    assert model["summary"]["success_rate"] == 0.0
