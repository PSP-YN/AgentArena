# AgentArena

Framework-independent benchmarking for AI agents: task success, tool calls, latency, token/cost accounting, reliability, and execution traces.

> Hackathon MVP in active development. The current prototype supports controlled tool-agent runs and resilience scenarios; its benchmark suite and scoring methodology are not yet externally validated.

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the architecture and measurement contract.

## Current implementation

- FastAPI service and browser dashboard
- Normalized exact-match and contains scorers
- Execution timing, step counts, tool-call metrics, and traces
- Repeated trial comparison across up to 3 Bifrost model routes
- Controlled Bifrost tool-using agent loop
- Safe calculator and synthetic-document tools (no shell/filesystem/network tools)
- Fault scenarios: one-time tool failure, misleading tool output, simulated provider outage
- Explicit unknown/null token and cost values rather than fabricated metrics
- Pytest and GitHub Actions CI

## Quick start

Requirements: Python 3.12+ and a running Bifrost gateway for live model calls.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Configure the gateway values in .env
uvicorn app.main:app --reload --env-file .env
```

Open the dashboard at http://localhost:8000 and API docs at http://localhost:8000/docs.

## Bifrost configuration

Start Bifrost (for example, with its official local Docker/NPX quickstart), configure at least one provider/model, then set:

```bash
export BIFROST_BASE_URL=http://localhost:8080
export BIFROST_API_KEY= # optional if your gateway requires it
export BIFROST_LOGS_API_KEY= # optional management key with Logs:View permission
```

The gateway adapter uses the OpenAI-compatible `/v1/chat/completions` endpoint. Live model comparison calls the tool-loop agent.

## API

- `GET /health`
- `GET /api/v1/tasks` — built-in controlled benchmark scenario catalog
- `POST /api/v1/runs` — manual adapter output to exercise scoring
- `POST /api/v1/bifrost-runs` — single Bifrost chat completion
- `POST /api/v1/bifrost-benchmarks` — compare up to 3 models across 1–5 repeats
- `GET /docs` — OpenAPI docs

Benchmark request:

```json
{
  "task_id": "tool-recovery-001",
  "prompt": "Use the calculator tool to calculate 19 * 23. Return only the result.",
  "expected_output": "437",
  "models": ["provider/model"],
  "repeats": 2,
  "fault_mode": "tool_error_once"
}
```

Supported `fault_mode` values:

- `none`
- `tool_error_once` — inject a temporary error on the first tool call
- `misleading_tool_output` — add an untrusted instruction to a synthetic document fixture
- `provider_outage` — simulate a provider outage and record failed trials

## Metric integrity and limitations

- Latency is measured around the adapter/agent run.
- Step count means Bifrost model request steps in the current tool loop.
- Tool calls count the model-emitted and executed allowlisted tool calls.
- Token counts are reported only when all model-step usage needed for aggregation is present.
- Cost is retrieved from Bifrost logs when BIFROST_LOGS_API_KEY has Logs:View permission and logging is enabled. Otherwise it remains unknown; it is not estimated.
- Fault-injection fixtures are synthetic and clearly separated from real external data.
- The current agent has a bounded loop and only two safe tools; arbitrary agent-framework adapters and more evaluation tasks remain future work.
- Exact-match scoring is intentionally simple and task-specific.

## Next

1. Persist runs and build cross-task leaderboards
2. Add adapters for external agent frameworks and endpoint protocols
3. Add broader task suites and rubric-based scorers
4. Improve statistical reporting, reliability analysis, and provider-failure tests
5. Validate metrics across repeated live runs

## Hackathon

Geek Room Global AI Hackathon — Bifrost Priority Track: “Build a Benchmarking Platform for AI Agents, Not Just Models.”


## Vercel environment

For hosted runs, configure these in the Vercel project settings (never commit them):

- `BIFROST_BASE_URL`: publicly/reachably hosted gateway URL. **Do not use localhost** for Vercel; that points to the serverless runtime, not your laptop.
- `BIFROST_API_KEY`: inference key if the gateway requires one.
- `BIFROST_LOGS_API_KEY`: separate management key with `Logs:View` permission to read actual cost records. Without it, cost remains unknown.


## Privacy

AgentArena sends benchmark prompts and tool messages to the configured Bifrost model/provider. Use non-sensitive tasks. Bifrost logging is controlled by your gateway configuration; the app does not persist benchmark history in a database in this MVP.
