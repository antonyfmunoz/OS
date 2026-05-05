---
type: codebase-function
file: eos_ai/substrate/station_drainer.py
line: 190
generated: 2026-04-12
---

# drain_results

**File:** [[eos_ai-substrate-station_drainer-py]] | **Line:** 190
**Signature:** `drain_results(node_id) → ResultDrainStats`

RESULT-ONLY drain. Reads the inbox, ingests result entries, skips events.

Prefer `drain_all()` in operator paths so events and results cannot
race each other across two drain_inbox() calls.

## Calls

- [[eos_ai-substrate-result_store-py-ResultStore-get]]
- [[eos_ai-substrate-result_store-py-_log]]
- [[eos_ai-substrate-station_bus-py-StationBus-drain_inbox]]
- [[eos_ai-substrate-station_bus-py-_log]]
- [[eos_ai-substrate-station_bus-py-get_station_bus]]
- [[eos_ai-substrate-station_drainer-py-_ingest_results]]
- [[eos_ai-substrate-station_drainer-py-_log]]

## Called By

- [[scripts-substrate_voice_session_smoke_test-py-_drain]]
