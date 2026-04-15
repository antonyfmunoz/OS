---
type: codebase-function
file: eos_ai/substrate/operator_interface.py
line: 295
generated: 2026-04-12
---

# assign_owner

**File:** [[eos_ai-substrate-operator_interface-py]] | **Line:** 295
**Signature:** `assign_owner(node_id, meeting_id) → dict[str, Any]`

Operator-triggered owner assignment. Updates matching commitment(s)
in-place on the in-memory summary. No external effects.

Returns {"updated": [...], "count": int}.

## Calls

- [[eos_ai-substrate-operator_interface-py-_get_summary]]
