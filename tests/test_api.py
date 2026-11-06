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


def test_database_required_blocks_inference_without_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTARENA_REQUIRE_DATABASE", "true")
    response = client.post("/api/v1/runs", json={
        "task_id": "db-required",
        "prompt": "Return answer",
        "expected_output": "done",
        "actual_output": "done",
    })
    assert response.status_code == 503
    assert "DATABASE_URL" in response.json()["detail"]


def test_manual_run_is_persisted_and_history_is_readable(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'agentarena.db'}")
    monkeypatch.delenv("AGENTARENA_REQUIRE_DATABASE", raising=False)
    run = client.post("/api/v1/runs", json={
        "task_id": "persist-test",
        "prompt": "Return answer",
        "expected_output": "done",
        "actual_output": "done",
    })
    assert run.status_code == 200
    history = client.get("/api/v1/history")
    assert history.status_code == 200
    assert history.json()["runs"][0]["run_id"] == run.json()["run_id"]


def test_history_is_protected_when_api_key_is_configured(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'agentarena.db'}")
    monkeypatch.setenv("AGENTARENA_API_KEY", "history-secret")
    assert client.get("/api/v1/history").status_code == 401
    response = client.get("/api/v1/history", headers={"x-api-key": "history-secret"})
    assert response.status_code == 200


def test_readiness_requires_database_when_configured(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENTARENA_REQUIRE_DATABASE", "true")
    assert client.get("/ready").status_code == 503


def test_readiness_checks_configured_database(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'ready.db'}")
    monkeypatch.setenv("AGENTARENA_REQUIRE_DATABASE", "true")
    monkeypatch.setenv("AGENTARENA_API_KEY", "production-secret")
    monkeypatch.setenv("BIFROST_BASE_URL", "https://gateway.example")
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["storage"] == "connected"
    assert response.json()["provider"] == "configured"


def test_bifrost_rejects_unknown_scorer_before_provider_call():
    response = client.post("/api/v1/bifrost-runs", json={
        "task_id": "invalid-scorer",
        "prompt": "This must not reach a model provider",
        "expected_output": "done",
        "model": "provider/model",
        "scorer": "made_up_scorer",
    })
    assert response.status_code == 422


def test_benchmark_model_route_length_is_bounded():
    response = client.post("/api/v1/bifrost-benchmarks", json={
        "task_id": "long-model",
        "prompt": "test",
        "expected_output": "done",
        "models": ["m" * 201],
        "repeats": 1,
    })
    assert response.status_code == 422



def test_production_readiness_fails_without_api_key(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'auth-required.db'}")
    monkeypatch.setenv("AGENTARENA_REQUIRE_DATABASE", "true")
    monkeypatch.delenv("AGENTARENA_API_KEY", raising=False)
    monkeypatch.setenv("BIFROST_BASE_URL", "https://gateway.example")
    assert client.get("/ready").status_code == 503


def test_production_readiness_rejects_localhost_gateway(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'gateway-required.db'}")
    monkeypatch.setenv("AGENTARENA_REQUIRE_DATABASE", "true")
    monkeypatch.setenv("AGENTARENA_API_KEY", "production-secret")
    monkeypatch.setenv("BIFROST_BASE_URL", "http://localhost:8080")
    assert client.get("/ready").status_code == 503


def test_production_inference_fails_closed_without_api_key(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'inference-auth.db'}")
    monkeypatch.setenv("AGENTARENA_REQUIRE_DATABASE", "true")
    monkeypatch.delenv("AGENTARENA_API_KEY", raising=False)
    response = client.post("/api/v1/runs", json={
        "task_id": "production-auth",
        "prompt": "Return answer",
        "expected_output": "done",
        "actual_output": "done",
    })
    assert response.status_code == 503
