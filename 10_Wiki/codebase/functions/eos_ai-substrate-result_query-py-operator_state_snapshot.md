---
type: codebase-function
file: eos_ai/substrate/result_query.py
line: 345
generated: 2026-04-12
---

# operator_state_snapshot

**File:** [[eos_ai-substrate-result_query-py]] | **Line:** 345
**Signature:** `operator_state_snapshot(node_id) → dict[str, Any]`

Bounded operator state view for a node (or all nodes if node_id is None).

Read-only. JSON-friendly. Best-effort — returns an empty shape on failure
so callers don't need to wrap.

## Calls

- [[eos_ai-substrate-result_query-py-stats]]
- [[eos_ai-substrate-result_store-py-IngestedResult-as_dict]]
- [[eos_ai-substrate-result_store-py-ResultStore-all]]
- [[eos_ai-substrate-result_store-py-ResultStore-get]]
- [[eos_ai-substrate-result_store-py-ResultStore-stats]]

## Called By

- [[scripts-substrate_operator_state_smoke_test-py-main]]
