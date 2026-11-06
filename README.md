# AgentArena

Framework-independent benchmarking for AI agents: task success, tool calls, latency, token/cost accounting, reliability, and execution traces.

> Early development — initial scaffold. Metrics will be labeled as measured, estimated, or unavailable; AgentArena will not fabricate benchmark results.

## Status

Project initialization is complete. The implementation roadmap and first benchmark engine are being developed.

## Planned stack

- Python 3.12+
- FastAPI API layer
- Pydantic task/agent contracts
- SQLite for local runs (initial)
- Pytest

## Design principles

- Repeatable tasks and explicit scoring criteria
- Per-run trace records
- Clear separation between observed metrics and estimates
- No API keys committed to source control
- Failure cases are first-class benchmark outcomes

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Planned modules

- `app/models.py`: task, agent, run and result schemas
- `app/runner.py`: isolated task execution and timing
- `app/metrics.py`: metrics aggregation
- `app/main.py`: API endpoints
- `tests/`: unit and integration tests

## Hackathon

Geek Room Global AI Hackathon — Bifrost Priority Track: “Build a Benchmarking Platform for AI Agents, Not Just Models.”
