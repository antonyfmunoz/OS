---
type: codebase-function
file: eos_ai/substrate/workflow_delegation.py
line: 398
generated: 2026-04-12
---

# enrich_metadata

**File:** [[eos_ai-substrate-workflow_delegation-py]] | **Line:** 398
**Signature:** `enrich_metadata(meta, text, mode) → dict[str, Any]`

Classify intent, resolve policy, and attach workflow metadata to *meta*.

Returns the same dict with workflow fields added (mutation + return).
This is the single call-site for the transport layer.

...

## Calls

- [[eos_ai-substrate-workflow_delegation-py-classify_workflow_intent]]
- [[eos_ai-substrate-workflow_delegation-py-resolve_workflow_policy]]
