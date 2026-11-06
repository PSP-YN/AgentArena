from pathlib import Path
import time
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.engine import AgentResponse, BenchmarkTask, run_task
from app.metrics import summarize_runs
from app.providers.bifrost import BifrostError, call_bifrost
from app.agents.bifrost_tool_agent import run_bifrost_tool_agent

app = FastAPI(title="AgentArena", version="0.1.0", description="Reproducible AI agent benchmark runner")


class RunRequest(BaseModel):
    task_id: str = Field(min_length=1)
    prompt: str
    expected_output: str
    actual_output: str
    agent_name: str = "manual-adapter"
    scorer: str = "normalized_exact_match"
    steps: int = Field(default=1, ge=1)
    tool_calls: int = Field(default=0, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost_usd: float | None = Field(default=None, ge=0)


class BifrostRunRequest(BaseModel):
    task_id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    expected_output: str
    model: str = Field(min_length=1, description="Bifrost model route, e.g. provider/model")
    scorer: str = "normalized_exact_match"


class BifrostBenchmarkRequest(BaseModel):
    task_id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    expected_output: str
    models: list[str] = Field(min_length=1, max_length=3)
    repeats: int = Field(default=2, ge=1, le=5)
    scorer: str = "normalized_exact_match"
    fault_mode: Literal["none", "tool_error_once", "misleading_tool_output", "provider_outage"] = "none"


@app.get("/")
def root():
    return RedirectResponse(url="/ui/")


@app.get("/health")
def health():
    return {"status": "ok", "service": "AgentArena", "version": "0.1.0"}


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

    return result.__dict__


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

    return result.__dict__


@app.post("/api/v1/bifrost-benchmarks")
def compare_bifrost_models(request: BifrostBenchmarkRequest):
    if len(set(request.models)) != len(request.models):
        raise HTTPException(status_code=422, detail="Model routes must be unique")

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
                record = result.__dict__
                record["trial"] = trial
            except BifrostError as exc:
                record = {
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


app.mount(
    "/ui",
    StaticFiles(directory=Path(__file__).resolve().parent.parent / "static", html=True),
    name="ui",
)
