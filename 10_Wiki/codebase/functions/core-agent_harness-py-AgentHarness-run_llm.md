---
type: codebase-function
file: core/agent_harness.py
line: 205
generated: 2026-04-12
---

# AgentHarness.run_llm

**File:** [[core-agent_harness-py]] | **Line:** 205
**Signature:** `run_llm(agent, prompt) → HarnessResult`

**Class:** [[core-agent_harness-py-AgentHarness]]

Run an LLM call on behalf of an agent.

Enforces CALL_LLM capability. Optionally enriches the prompt with
graph search hits (only when the agent has READ_GRAPH). Returns a
HarnessResult with output=str content.

## Calls

- [[core-agent_harness-py-AgentHarness-_fail]]
- [[core-agent_harness-py-AgentHarness-_log]]
- [[core-agent_harness-py-AgentHarness-_router]]
- [[core-agent_harness-py-AgentHarness-graph_search]]
- [[core-agent_harness-py-AgentHarness-profile]]
- [[core-agent_harness-py-_routing_output]]
- [[core-agent_harness-py-_routing_provider]]
- [[core-capability-py-CapabilityEnforcer-may]]

## Called By

- [[core-agent_harness-py-AgentHarness-run_with_advisor]]
- [[core-persistent_agents-py-LibrarianAgent-tick_impl]]
