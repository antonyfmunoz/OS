---
type: codebase-function
file: eos_ai/substrate/operator_interface.py
line: 106
generated: 2026-05-07
---

# get_top_actionable

**File:** [[eos_ai-substrate-operator_interface-py]] | **Line:** 106
**Signature:** `get_top_actionable(node_id, meeting_id) → Optional[dict[str, Any]]`

Return highest-priority actionable. Ties broken by readiness
(ready > blocked) then by original snapshot order (stable).

## Calls

- [[eos_ai-substrate-operator_interface-py-_items]]
- [[eos_ai-substrate-operator_interface-py-_safe_snapshot]]
