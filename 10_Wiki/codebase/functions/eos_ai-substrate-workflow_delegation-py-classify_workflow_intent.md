---
type: codebase-function
file: eos_ai/substrate/workflow_delegation.py
line: 181
generated: 2026-05-07
---

# classify_workflow_intent

**File:** [[eos_ai-substrate-workflow_delegation-py]] | **Line:** 181
**Signature:** `classify_workflow_intent(text, mode, metadata) → dict[str, Any]`

Classify a request into intent + workflow kind.

Returns::

    {
...

## Calls

- [[eos_ai-substrate-workflow_delegation-py-_check_extra_keywords]]
- [[eos_ai-substrate-workflow_delegation-py-_result]]

## Called By

- [[eos_ai-substrate-workflow_delegation-py-enrich_metadata]]
- [[eos_ai-substrate-workflow_execution-py-execute_workflow_if_allowed]]
