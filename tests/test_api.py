from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "AgentArena"


def test_manual_benchmark_endpoint():
    response = client.post("/api/v1/runs", json={
        "task_id": "api-test",
        "prompt": "Return answer",
        "expected_output": "done",
        "actual_output": "done",
    })
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["score"] == 1.0
