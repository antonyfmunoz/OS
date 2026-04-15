---
type: codebase-function
file: eos_ai/substrate/result_query.py
line: 111
generated: 2026-04-12
---

# node_health_summary

**File:** [[eos_ai-substrate-result_query-py]] | **Line:** 111
**Signature:** `node_health_summary(node_id) → dict[str, Any]`

Tiny operator-facing health view for a single node: counts by status,
counts by kind, fallback count, last ingested_at.

## Calls

- [[eos_ai-substrate-result_store-py-ResultStore-by_node]]
- [[eos_ai-substrate-result_store-py-ResultStore-get]]
- [[eos_ai-substrate-result_store-py-get_result_store]]

## Called By

- [[eos_ai-substrate-station_readiness-py-station_readiness]]
- [[scripts-substrate_drain_station-py-main]]
- [[scripts-substrate_durable_result_smoke_test-py-main]]
