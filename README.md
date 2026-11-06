# AgentArena

Framework-independent benchmarking for AI agents: task success, tool calls, latency, token/cost accounting, reliability, and execution traces.

> Hackathon MVP in active development. The API and UI are an early prototype; results are not yet a validated benchmark suite.

## Current implementation

- FastAPI service and browser dashboard
- Deterministic normalized exact-match and contains scorers
- Execution timing and trace capture
- Explicit unknown/null token and cost values rather than fabricated metrics
- Bifrost OpenAI-compatible Chat Completions adapter
- Manual-output route for testing scoring separately from model execution
- Pytest and GitHub Actions CI

## Quick start

Requirements: Python 3.12+ and a running Bifrost gateway for live model calls.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open the dashboard at http://localhost:8000 and API docs at http://localhost:8000/docs.

## Bifrost configuration

Start Bifrost (for example, with its official local Docker/NPX quickstart), configure at least one provider/model, then set:

```bash
export BIFROST_BASE_URL=http://localhost:8080
export BIFROST_API_KEY= # optional if your gateway requires it
```

The dashboard's live mode sends a model route such as `openai/gpt-4o-mini` to `POST /api/v1/bifrost-runs`. The adapter calls Bifrost's OpenAI-compatible `/v1/chat/completions` endpoint.

## API

- `GET /health`
- `POST /api/v1/runs` — manual adapter output, to exercise the scorer
- `POST /api/v1/bifrost-runs` — live Bifrost model call and scoring
- `GET /docs` — OpenAPI docs

Example request:

```json
{
  "task_id": "exact-match-001",
  "prompt": "Answer with one word: Paris",
  "expected_output": "Paris",
  "model": "openai/gpt-4o-mini",
  "scorer": "normalized_exact_match"
}
```

## Metric integrity

- Latency is measured by the app around the adapter call.
- Token counts are reported only when the gateway returns usage.
- Tool calls are currently counted from returned message tool calls; this is not yet a full tool-execution trace.
- Cost is unknown unless a trusted cost source is added; it is not estimated.
- Exact-match scoring is intentionally simple. More task types and rubric-based evaluators are planned.

## Next

1. Persist runs and compare repeated trials
2. Add agent adapters and benchmark task catalog
3. Add failure injection and outage testing
4. Improve traces, evaluation criteria and statistical summaries
5. Validate metrics across repeated real runs

## Hackathon

Geek Room Global AI Hackathon — Bifrost Priority Track: “Build a Benchmarking Platform for AI Agents, Not Just Models.”
