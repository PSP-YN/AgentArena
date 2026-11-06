from pathlib import Path
import os
import time
import hmac
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel, Field

from app.engine import AgentResponse, BenchmarkTask, run_task
from app.metrics import summarize_runs
from app.providers.bifrost import BifrostError, call_bifrost, attach_trace_cost
from app.agents.bifrost_tool_agent import run_bifrost_tool_agent
from app.tasks import BUILTIN_TASKS
from app.storage import check_storage, list_results, save_result, storage_enabled
import uuid

app = FastAPI(
    title="AgentArena",
    version="0.2.0",
    description="Reproducible AI agent benchmark runner",
)


@app.middleware("http")
async def protect_expensive_api_routes(request: Request, call_next):
    """Optional API-key protection for endpoints that can trigger inference/cost.

    Set AGENTARENA_API_KEY in production. Local development remains frictionless
    when the variable is unset. The key is never returned in responses.
    """
    protected = {
        "/api/v1/runs",
        "/api/v1/bifrost-runs",
        "/api/v1/bifrost-benchmarks",
        "/api/v1/history",
    }
    if (
        request.method == "POST"
        and request.url.path in protected
        and os.getenv("AGENTARENA_REQUIRE_DATABASE", "false").lower() in {"1", "true", "yes"}
        and not storage_enabled()
    ):
        return JSONResponse(
            status_code=503,
            content={"detail": "Durable storage is required but DATABASE_URL is not configured"},
        )
    configured_key = os.getenv("AGENTARENA_API_KEY", "").strip()
    requires_auth = (
        (request.method == "POST" and request.url.path in protected - {"/api/v1/history"})
        or (request.method == "GET" and request.url.path == "/api/v1/history")
    )
    if requires_auth and configured_key:
        supplied = request.headers.get("x-api-key", "")
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            supplied = authorization[7:].strip()
        if not supplied or not hmac.compare_digest(supplied, configured_key):
            return JSONResponse(
                status_code=401,
                content={"detail": "Valid API key required"},
                headers={"WWW-Authenticate": "Bearer"},
            )
    return await call_next(request)


class RunRequest(BaseModel):
    task_id: str = Field(min_length=1, max_length=120)
    prompt: str = Field(max_length=12000)
    expected_output: str = Field(max_length=4000)
    actual_output: str = Field(max_length=12000)
    agent_name: str = Field(default="manual-adapter", max_length=120)
    scorer: str = Field(default="normalized_exact_match", max_length=64)
    steps: int = Field(default=1, ge=1, le=1000)
    tool_calls: int = Field(default=0, ge=0, le=10000)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)


class BifrostRunRequest(BaseModel):
    task_id: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=12000)
    expected_output: str = Field(max_length=4000)
    model: str = Field(min_length=1, max_length=200, description="Bifrost model route, e.g. provider/model")
    scorer: str = Field(default="normalized_exact_match", max_length=64)


class BifrostBenchmarkRequest(BaseModel):
    task_id: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=12000)
    expected_output: str = Field(max_length=4000)
    models: list[str] = Field(min_length=1, max_length=3)
    repeats: int = Field(default=2, ge=1, le=5)
    scorer: str = Field(default="normalized_exact_match", max_length=64)
    fault_mode: Literal["none", "tool_error_once", "misleading_tool_output", "provider_outage"] = "none"


@app.get("/")
def root():
    return RedirectResponse(url="/ui/")


@app.get("/api/v1/tasks")
def list_tasks():
    return {"tasks": BUILTIN_TASKS}


@app.get("/health")
def health():
    return {"status": "ok", "service": "AgentArena", "version": app.version}


@app.get("/ready")
def readiness():
    required = os.getenv("AGENTARENA_REQUIRE_DATABASE", "false").lower() in {"1", "true", "yes"}
    if not storage_enabled():
        if required:
            raise HTTPException(status_code=503, detail="Durable storage is required but DATABASE_URL is not configured")
        return {"status": "ready", "storage": "disabled"}
    try:
        check_storage()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database readiness check failed") from exc
    return {"status": "ready", "storage": "connected"}


@app.post("/api/v1/runs")
def create_run(request: RunRequest):
    task = BenchmarkTask(
        task_id=request.task_id,
        prompt=request.prompt,
        expected_output=request.expected_output,
        scorer=request.scorer,
    )

    def adapter(_prompt: str) -> AgentResponse:
        return AgentResponse(
            output=request.actual_output,
            steps=request.steps,
            tool_calls=request.tool_calls,
            input_tokens=request.input_tokens,
            output_tokens=request.output_tokens,
            cost_usd=request.cost_usd,
            trace=[{"event": "adapter_output_received", "adapter": request.agent_name}],
        )

    try:
        result = run_task(task, request.agent_name, adapter)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    record = result.__dict__
    if storage_enabled():
        try:
            save_result(record, "manual")
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Benchmark completed but could not be saved to durable history") from exc
    return record


@app.post("/api/v1/bifrost-runs")
def create_bifrost_run(request: BifrostRunRequest):
    task = BenchmarkTask(
        task_id=request.task_id,
        prompt=request.prompt,
        expected_output=request.expected_output,
        scorer=request.scorer,
    )

    def adapter(prompt: str) -> AgentResponse:
        return call_bifrost(prompt, request.model)

    try:
        result = run_task(task, f"bifrost:{request.model}", adapter)
    except BifrostError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    record = attach_trace_cost(result.__dict__)
    if storage_enabled():
        try:
            save_result(record, "bifrost_single")
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Benchmark completed but could not be saved to durable history") from exc
    return record


@app.post("/api/v1/bifrost-benchmarks")
def compare_bifrost_models(request: BifrostBenchmarkRequest):
    if len(set(request.models)) != len(request.models):
        raise HTTPException(status_code=422, detail="Model routes must be unique")
    if any(not model.strip() for model in request.models):
        raise HTTPException(status_code=422, detail="Model routes cannot be blank")

    task = BenchmarkTask(
        task_id=request.task_id,
        prompt=request.prompt,
        expected_output=request.expected_output,
        scorer=request.scorer,
    )
    comparisons = []

    for model in request.models:
        runs = []
        for trial in range(1, request.repeats + 1):
            started = time.perf_counter()
            try:
                result = run_task(
                    task,
                    f"bifrost-tool-agent:{model}",
                    lambda prompt: run_bifrost_tool_agent(prompt, model, request.fault_mode),
                )
                record = attach_trace_cost(result.__dict__)
                record["trial"] = trial
            except BifrostError as exc:
                record = {
                    "run_id": str(uuid.uuid4()),
                    "task_id": task.task_id,
                    "agent_name": f"bifrost-tool-agent:{model}",
                    "success": False,
                    "score": 0.0,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                    "steps": 0,
                    "tool_calls": 0,
                    "input_tokens": None,
                    "output_tokens": None,
                    "cost_usd": None,
                    "output": None,
                    "error": str(exc),
                    "trial": trial,
                }
            record["model"] = model
            record["fault_mode"] = request.fault_mode
            if storage_enabled():
                try:
                    save_result(record, "bifrost_comparison")
                except Exception as exc:
                    raise HTTPException(status_code=503, detail="Benchmark completed but could not be saved to durable history") from exc
            runs.append(record)

        comparisons.append({
            "model": model,
            "runs": runs,
            "summary": summarize_runs(runs),
        })

    return {
        "task_id": task.task_id,
        "repeats_per_model": request.repeats,
        "fault_mode": request.fault_mode,
        "models": comparisons,
        "note": "Observed metrics only. Cost is null unless all runs provide trusted cost values.",
    }


@app.get("/api/v1/history")
def benchmark_history(limit: int = 25, offset: int = 0):
    if not storage_enabled():
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured; durable history is unavailable")
    if limit < 1 or limit > 100 or offset < 0:
        raise HTTPException(status_code=422, detail="limit must be 1–100 and offset must be non-negative")
    try:
        return {"runs": list_results(limit=limit, offset=offset), "limit": limit, "offset": offset}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Could not read durable benchmark history") from exc


app.mount(
    "/ui",
    StaticFiles(directory=Path(__file__).resolve().parent.parent / "static", html=True),
    name="ui",
)
