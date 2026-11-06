import pytest
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


def test_expensive_api_requires_key_when_configured(monkeypatch):
    monkeypatch.setenv("AGENTARENA_API_KEY", "test-secret")
    payload = {
        "task_id": "secure-test",
        "prompt": "Return answer",
        "expected_output": "done",
        "actual_output": "done",
    }
    assert client.post("/api/v1/runs", json=payload).status_code == 401
    response = client.post(
        "/api/v1/runs",
        json=payload,
        headers={"Authorization": "Bearer test-secret"},
    )
    assert response.status_code == 200


def test_api_key_header_supported(monkeypatch):
    monkeypatch.setenv("AGENTARENA_API_KEY", "test-secret")
    response = client.post(
        "/api/v1/runs",
        json={
            "task_id": "secure-test",
            "prompt": "Return answer",
            "expected_output": "done",
            "actual_output": "done",
        },
        headers={"x-api-key": "test-secret"},
    )
    assert response.status_code == 200


def test_request_limits_are_validated():
    response = client.post("/api/v1/runs", json={
        "task_id": "limit-test",
        "prompt": "x" * 12001,
        "expected_output": "done",
        "actual_output": "done",
    })
    assert response.status_code == 422


def test_health_is_public_when_api_key_enabled(monkeypatch):
    monkeypatch.setenv("AGENTARENA_API_KEY", "test-secret")
    assert client.get("/health").status_code == 200
