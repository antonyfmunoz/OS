---
type: codebase-function
file: eos_ai/substrate/station_triggers.py
line: 181
generated: 2026-05-07
---

# StationTriggerStore.put

**File:** [[eos_ai-substrate-station_triggers-py]] | **Line:** 181
**Signature:** `put(event) → None`

**Class:** [[eos_ai-substrate-station_triggers-py-StationTriggerStore]]

Persist an event.  Prunes if over capacity.

## Calls

- [[eos_ai-substrate-station_triggers-py-StationTriggerStore-_flush]]
- [[eos_ai-substrate-station_triggers-py-StationTriggerStore-_prune]]

## Called By

- [[eos_ai-substrate-station_triggers-py-StationTriggerStore-_flush]]
- [[eos_ai-substrate-station_triggers-py-register_station_trigger]]
