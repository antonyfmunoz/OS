---
type: codebase-function
file: eos_ai/substrate/operator_interface.py
line: 84
generated: 2026-04-12
---

# get_actionable_items

**File:** [[eos_ai-substrate-operator_interface-py]] | **Line:** 84
**Signature:** `get_actionable_items(node_id, meeting_id) → list[dict[str, Any]]`

Return actionable items for (node_id, meeting_id), optionally filtered.

Supported filter keys:
    readiness_state : str in _VALID_READINESS
    owner           : str  (exact match)
...

## Calls

- [[eos_ai-substrate-operator_interface-py-_items]]
- [[eos_ai-substrate-operator_interface-py-_match]]
- [[eos_ai-substrate-operator_interface-py-_safe_snapshot]]

## Called By

- [[eos_ai-substrate-operator_interface-py-get_blocked_items]]
- [[eos_ai-substrate-operator_interface-py-get_owner_breakdown]]
- [[eos_ai-substrate-operator_interface-py-get_ready_items]]
