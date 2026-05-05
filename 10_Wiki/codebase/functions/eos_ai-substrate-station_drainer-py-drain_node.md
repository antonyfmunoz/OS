---
type: codebase-function
file: eos_ai/substrate/station_drainer.py
line: 161
generated: 2026-04-12
---

# drain_node

**File:** [[eos_ai-substrate-station_drainer-py]] | **Line:** 161
**Signature:** `drain_node(node_id) → DrainStats`

EVENT-ONLY drain. Kept for backwards compatibility with the earlier
drainer pass. Reads the inbox, ingests events, skips results.

For a full drain (events + results) prefer `drain_all()` — it reads
the inbox only once and updates both sinks atomically.

## Calls

- [[eos_ai-substrate-result_store-py-ResultStore-get]]
- [[eos_ai-substrate-result_store-py-_log]]
- [[eos_ai-substrate-station_bus-py-StationBus-drain_inbox]]
- [[eos_ai-substrate-station_bus-py-_log]]
- [[eos_ai-substrate-station_bus-py-get_station_bus]]
- [[eos_ai-substrate-station_drainer-py-_ingest_events]]
- [[eos_ai-substrate-station_drainer-py-_log]]

## Called By

- [[scripts-substrate_drainer_smoke_test-py-main]]
