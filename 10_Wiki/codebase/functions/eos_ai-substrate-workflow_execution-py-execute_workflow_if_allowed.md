---
type: codebase-function
file: eos_ai/substrate/workflow_execution.py
line: 240
generated: 2026-04-12
---

# execute_workflow_if_allowed

**File:** [[eos_ai-substrate-workflow_execution-py]] | **Line:** 240
**Signature:** `execute_workflow_if_allowed(text, mode) → dict[str, Any]`

Classify, policy-check, and execute a workflow request.

This is the single entry point for the execution layer.  It chains
classification (workflow_delegation) with handler dispatch (this module).

...

## Calls

- [[eos_ai-substrate-workflow_delegation-py-classify_workflow_intent]]
- [[eos_ai-substrate-workflow_delegation-py-resolve_workflow_policy]]
- [[eos_ai-substrate-workflow_execution-py-_resolve_handler]]
