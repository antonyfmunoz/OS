---
type: codebase-class
file: core/agent_harness.py
line: 113
generated: 2026-04-12
---

# AgentHarness

**File:** [[core-agent_harness-py]] | **Line:** 113

Single execution surface. One instance per process is sufficient.

## Methods

- [[core-agent_harness-py-AgentHarness-__init__]]`() → None` — 
- [[core-agent_harness-py-AgentHarness-register_profile]]`(profile) → None` — 
- [[core-agent_harness-py-AgentHarness-profile]]`(agent) → CapabilityProfile` — 
- [[core-agent_harness-py-AgentHarness-agents]]`() → list[str]` — 
- [[core-agent_harness-py-AgentHarness-_actions]]`() → Any` — 
- [[core-agent_harness-py-AgentHarness-_graph]]`() → Any` — 
- [[core-agent_harness-py-AgentHarness-_memory]]`() → Any` — 
- [[core-agent_harness-py-AgentHarness-_router]]`() → Callable[..., Any] | None` — 
- [[core-agent_harness-py-AgentHarness-run_llm]]`(agent, prompt) → HarnessResult` — Run an LLM call on behalf of an agent.
- [[core-agent_harness-py-AgentHarness-run_action]]`(agent, action_type, target) → HarnessResult` — Propose + execute an action through the action system.
- [[core-agent_harness-py-AgentHarness-run_with_advisor]]`(agent, task, context, metadata) → HarnessResult` — Run an LLM call with conditional advisor escalation.
- [[core-agent_harness-py-AgentHarness-graph_search]]`(agent, term) → HarnessResult` — 
- [[core-agent_harness-py-AgentHarness-remember]]`(agent, content) → HarnessResult` — Write a free-form note to AgentMemory on behalf of an agent.
- [[core-agent_harness-py-AgentHarness-_fail]]`(method, agent, reason, t0) → HarnessResult` — 
- [[core-agent_harness-py-AgentHarness-_log]]`(result) → None` — 
