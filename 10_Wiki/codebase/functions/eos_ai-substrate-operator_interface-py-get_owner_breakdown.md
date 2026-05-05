---
type: codebase-function
file: eos_ai/substrate/operator_interface.py
line: 150
generated: 2026-04-12
---

# get_owner_breakdown

**File:** [[eos_ai-substrate-operator_interface-py]] | **Line:** 150
**Signature:** `get_owner_breakdown(node_id, meeting_id) → dict[str, Any]`

Return ownership distribution across actionable items.

Shape:
    {
      "counts": {owner: count, ...},
...

## Calls

- [[eos_ai-substrate-operator_interface-py-get_actionable_items]]
