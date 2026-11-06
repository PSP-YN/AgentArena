# AgentArena live demo

## Setup

1. Run Bifrost locally and configure at least one provider/model route.
2. Start the app with `uvicorn app.main:app --reload`.
3. Open the dashboard and confirm the API is online.
4. Use a low-cost model route and set repeated trials to 2 for a short demo.

## Suggested 4-minute walkthrough

### 1. Establish the benchmark

- Select the built-in calculator retry scenario.
- Explain that the prompt, expected output, scorer, and injected fault are controlled.
- Run two trials with the same model route.

### 2. Show resilience and trace

- The first calculator tool invocation receives an injected temporary error.
- The agent receives the tool error in the conversation and can retry.
- Show the model-step trace, tool-call count, and final exact-match score.
- If the model fails to recover, show that failure as a measured result rather than hiding it.

### 3. Prompt-injection resistance

- Select the synthetic-document injection scenario.
- The lookup tool returns a document containing a malicious quoted instruction.
- The agent system prompt explicitly treats tool output as untrusted.
- The expected answer is the document's status, not the embedded malicious instruction.

### 4. Provider outage

- Select the simulated provider outage scenario.
- Explain that the platform records a failed trial, duration, and unknown metrics rather than dropping the failure or inventing a score.

### 5. Compare models

- Enter 2–3 Bifrost model routes.
- Run identical tasks and repeats.
- Compare success rate, score, mean latency, model-step count, tool calls, token usage, and cost status.

## Technical explanation

- AgentArena uses a framework-independent callable agent contract: prompt in, AgentResponse out.
- Bifrost is the gateway for model requests; model routes are configurable.
- Tool execution is bounded to an allowlisted calculator and a synthetic document fixture.
- Latency and usage are observed. Costs remain unknown unless the gateway supplies trusted cost data.
- The current benchmark set is small and synthetic; broader task suites and statistical validation are future work.
