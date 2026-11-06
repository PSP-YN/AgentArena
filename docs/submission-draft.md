# AgentArena — Hackathon submission draft

> **DRAFT ONLY — not submitted.** Requires project owner review, live integration verification, and final approval.

## Track and problem statement

- Track: Bifrost Priority Track
- Problem statement: Build a Benchmarking Platform for AI Agents, Not Just Models

## Project summary

AgentArena is a framework-independent evaluation platform for comparing AI agent behavior on identical tasks. It measures task success, execution latency, model steps, tool calls, token usage, and cost when trusted cost data is available. Repeated trials and controlled fault injection help expose reliability differences that a single model response cannot show.

## Problem

Model-only evaluations do not adequately capture agent execution behavior. Agents can fail due to tool errors, provider outages, or misleading tool output even when their underlying model is capable.

## Solution

AgentArena provides a controlled benchmark runner, a Bifrost-backed tool-using agent, a small task catalog, repeatable runs, failure scenarios, and an inspectable report.

## Implemented prototype capabilities

- Bifrost OpenAI-compatible model routing
- Repeated trials across up to three model routes
- Controlled calculator and synthetic-document tools
- Temporary tool failure injection
- Prompt-injection/misleading-tool-output fixture
- Simulated provider outage
- Success rate, score, latency, steps, tool-call and token metrics
- Unknown cost values are preserved rather than estimated
- Browser dashboard and API

## Technology and AI usage

- Python / FastAPI
- Bifrost gateway and configured model providers
- Pydantic
- HTTPX
- Pytest / GitHub Actions
- HTML/CSS/JavaScript dashboard

AI is used for agent execution and tool selection through Bifrost. AgentArena itself calculates benchmark scores and aggregate metrics deterministically for the current exact-match scorer.

## Repository

https://github.com/PSP-YN/AgentArena

## Demo

See [demo-script.md](demo-script.md).

## Known limitations to disclose

- Small controlled task suite; not a comprehensive industry benchmark
- Exact-match and contains scorers are limited
- Only a small safe tool sandbox is implemented
- Arbitrary external framework adapters are not yet available
- Cost is unknown unless a trusted provider/gateway cost source is supplied
- No persistent leaderboard/history yet

## Submission checklist

- [ ] Verify live Bifrost provider and model route
- [ ] Run all resilience scenarios with actual model calls
- [ ] Review results and ensure no fabricated metrics
- [ ] Record demo video
- [ ] Finalize pitch deck
- [ ] Owner review and explicit approval
- [ ] Submit only after approval
