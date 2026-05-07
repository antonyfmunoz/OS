---
type: codebase-class
file: eos_ai/substrate/station_triggers.py
line: 125
generated: 2026-05-07
---

# StationTriggerStore

**File:** [[eos_ai-substrate-station_triggers-py]] | **Line:** 125

Bounded, persistent event store for station triggers.

Dual-layer: in-memory dict + substrate.storage.  Thread-safe singleton.
Bounded to _MAX_EVENTS entries; oldest events pruned first.

## Methods

- [[eos_ai-substrate-station_triggers-py-StationTriggerStore-__init__]]`() → None` — 
- [[eos_ai-substrate-station_triggers-py-StationTriggerStore-_load]]`() → None` — 
- [[eos_ai-substrate-station_triggers-py-StationTriggerStore-_flush]]`() → None` — 
- [[eos_ai-substrate-station_triggers-py-StationTriggerStore-_prune]]`() → None` — Drop oldest events when over _MAX_EVENTS.  Caller holds lock.
- [[eos_ai-substrate-station_triggers-py-StationTriggerStore-put]]`(event) → None` — Persist an event.  Prunes if over capacity.
- [[eos_ai-substrate-station_triggers-py-StationTriggerStore-recent]]`(limit) → list[StationTriggerEvent]` — Return the most recent N events, newest first.
- [[eos_ai-substrate-station_triggers-py-StationTriggerStore-all]]`() → list[StationTriggerEvent]` — Return all events, newest first.
- [[eos_ai-substrate-station_triggers-py-StationTriggerStore-default]]`() → StationTriggerStore` — Return the process-wide singleton store.
- [[eos_ai-substrate-station_triggers-py-StationTriggerStore-reset_default_for_tests]]`() → None` — Test hook — drop the singleton.
