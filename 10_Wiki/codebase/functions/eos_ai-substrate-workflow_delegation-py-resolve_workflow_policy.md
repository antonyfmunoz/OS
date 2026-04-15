---
type: codebase-function
file: eos_ai/substrate/workflow_delegation.py
line: 309
generated: 2026-04-12
---

# resolve_workflow_policy

**File:** [[eos_ai-substrate-workflow_delegation-py]] | **Line:** 309
**Signature:** `resolve_workflow_policy(mode, intent_result) → dict[str, Any]`

Decide whether a classified workflow intent is allowed in the current mode.

Returns::

    {
...

## Calls

- [[eos_ai-substrate-workflow_delegation-py-_policy_result]]

## Called By

- [[eos_ai-substrate-workflow_delegation-py-enrich_metadata]]
- [[eos_ai-substrate-workflow_execution-py-execute_workflow_if_allowed]]
