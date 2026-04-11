---
type: codebase-function
file: eos_ai/substrate/operator_interface.py
line: 230
generated: 2026-04-11
---

# mark_resolved

**File:** [[eos_ai-substrate-operator_interface-py]] | **Line:** 230
**Signature:** `mark_resolved(node_id, meeting_id) → dict[str, Any]`

Operator-triggered resolution of commitments on a meeting summary.

Two modes:
    1. No selector (text_contains=None, owner=None) — delegate to
       meeting_intelligence.resolve_commitments (phrase-based).
...

## Calls

- [[eos_ai-substrate-operator_interface-py-_get_summary]]
