---
type: codebase-function
file: core/agent_harness.py
line: 435
generated: 2026-05-07
---

# AgentHarness.run_with_advisor

**File:** [[core-agent_harness-py]] | **Line:** 435
**Signature:** `run_with_advisor(agent, task, context, metadata) → HarnessResult`

**Class:** [[core-agent_harness-py-AgentHarness]]

Run an LLM call with conditional advisor escalation.

Flow:
  1. Execute task with fast model (executor)
  2. Evaluate result with escalation rules
...

## Calls

- [[core-agent_harness-py-AgentHarness-_log]]
- [[core-agent_harness-py-AgentHarness-run_llm]]

## Called By

- [[core-persistent_agents-py-LibrarianAgent-tick_impl]]
