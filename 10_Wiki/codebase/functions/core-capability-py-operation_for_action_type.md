---
type: codebase-function
file: core/capability.py
line: 467
generated: 2026-05-07
---

# operation_for_action_type

**File:** [[core-capability-py]] | **Line:** 467
**Signature:** `operation_for_action_type(action_type) → OperationKind`

Translate an ActionSystem action_type string into an OperationKind.

This lives here (not in action_system) so action_system can stay free of
capability imports — the harness is the bridge.

## Called By

- [[core-agent_harness-py-AgentHarness-run_action]]
- [[scripts-action_system-py-ActionSystem-_security_check]]
