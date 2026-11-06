from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.engine import AgentResponse, BenchmarkTask, run_task
from app.providers.bifrost import BifrostError, call_bifrost

app = FastAPI(title="AgentArena", version="0.1.0", description="Reproducible AI agent benchmark runner")


class RunRequest(BaseModel):
    task_id: str = Field(min_length=1)
    prompt: str
    expected_output: str
    actual_output: str
    agent_name: str = "manual-adapter"
    scorer: str = "normalized_exact_match"
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
