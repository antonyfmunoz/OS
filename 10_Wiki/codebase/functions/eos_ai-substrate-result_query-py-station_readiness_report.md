---
type: codebase-function
file: eos_ai/substrate/result_query.py
line: 188
generated: 2026-04-12
---

# station_readiness_report

**File:** [[eos_ai-substrate-result_query-py]] | **Line:** 188
**Signature:** `station_readiness_report(node_id) → dict[str, Any]`

Operator-facing readiness snapshot for a single node, paired with the
scene the policy layer would currently recommend AND the scene that
ritual inference would propose if no explicit hint were supplied.

Bounded, JSON-friendly, never raises. Safe to embed in operator reports.

## Calls

- [[eos_ai-substrate-result_store-py-ResultStore-get]]

## Called By

- [[scripts-substrate_drain_station-py-main]]
