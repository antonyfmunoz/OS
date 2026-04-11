---
type: codebase-function
file: eos_ai/substrate/station_readiness.py
line: 141
generated: 2026-04-11
---

# station_readiness

**File:** [[eos_ai-substrate-station_readiness-py]] | **Line:** 141
**Signature:** `station_readiness(node_id) → StationReadiness`

Compute readiness for a node. Always returns a StationReadiness object;
never raises. UNAVAILABLE is the safe default when data is missing.

## Calls

- [[eos_ai-substrate-nodes-py-NodeRegistry-default]]
- [[eos_ai-substrate-nodes-py-NodeRegistry-get]]
- [[eos_ai-substrate-result_query-py-node_health_summary]]
- [[eos_ai-substrate-result_store-py-ResultStore-by_node]]
- [[eos_ai-substrate-result_store-py-ResultStore-get]]
- [[eos_ai-substrate-result_store-py-get_result_store]]
- [[eos_ai-substrate-station_readiness-py-_age_seconds]]
- [[eos_ai-substrate-station_readiness-py-_count_unresolved_for_node]]

## Called By

- [[eos_ai-substrate-local_listener-py-LocalListener-_activate]]
- [[eos_ai-substrate-ritual_body-py-run_close_day_body]]
- [[eos_ai-substrate-ritual_body-py-run_open_day_body]]
- [[eos_ai-substrate-station_readiness-py-is_ready]]
