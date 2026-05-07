---
type: codebase-function
file: eos_ai/substrate/station_drainer.py
line: 215
generated: 2026-05-07
---

# drain_all

**File:** [[eos_ai-substrate-station_drainer-py]] | **Line:** 215
**Signature:** `drain_all(node_id) → DrainAllStats`

Unified drain: one inbox read, both sinks populated.

Use this in operator/loop contexts so event and result ingestion stay
in lockstep. A single drain_inbox() call atomically clears everything,
so there is no window where events and results can diverge.

## Calls

- [[eos_ai-substrate-result_store-py-ResultStore-get]]
- [[eos_ai-substrate-result_store-py-_log]]
- [[eos_ai-substrate-station_bus-py-StationBus-drain_inbox]]
- [[eos_ai-substrate-station_bus-py-_log]]
- [[eos_ai-substrate-station_bus-py-get_station_bus]]
- [[eos_ai-substrate-station_drainer-py-_ingest_events]]
- [[eos_ai-substrate-station_drainer-py-_ingest_results]]
- [[eos_ai-substrate-station_drainer-py-_log]]

## Called By

- [[eos_ai-substrate-station_drainer-py-drain_nodes]]
- [[scripts-substrate_drain_station-py-main]]
- [[scripts-substrate_durable_result_smoke_test-py-main]]
- [[scripts-substrate_result_loop_smoke_test-py-main]]
