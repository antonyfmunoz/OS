---
type: codebase-function
file: core/agent_harness.py
line: 309
generated: 2026-05-07
---

# AgentHarness.run_action

**File:** [[core-agent_harness-py]] | **Line:** 309
**Signature:** `run_action(agent, action_type, target) → HarnessResult`

**Class:** [[core-agent_harness-py-AgentHarness]]

Propose + execute an action through the action system.

Enforces capability based on (action_type, critical_hub_flag, risk).
The action system still does its own risk assessment; this is
defense in depth. If the agent lacks capability, nothing touches
...

## Calls

- [[core-agent_harness-py-AgentHarness-_actions]]
- [[core-agent_harness-py-AgentHarness-_fail]]
- [[core-agent_harness-py-AgentHarness-_log]]
- [[core-agent_harness-py-AgentHarness-profile]]
- [[core-capability-py-CapabilityEnforcer-may]]
- [[core-capability-py-operation_for_action_type]]
