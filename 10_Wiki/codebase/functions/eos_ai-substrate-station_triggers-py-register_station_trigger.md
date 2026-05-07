---
type: codebase-function
file: eos_ai/substrate/station_triggers.py
line: 227
generated: 2026-05-07
---

# register_station_trigger

**File:** [[eos_ai-substrate-station_triggers-py]] | **Line:** 227
**Signature:** `register_station_trigger(trigger_type, phrase) → StationTriggerEvent`

Register a trigger event and update station presence.

Creates a StationTriggerEvent, persists it, and best-effort updates
the station_presence and voice_wake state for backward compatibility.

## Calls

- [[eos_ai-substrate-station_triggers-py-StationTriggerEvent-new]]
- [[eos_ai-substrate-station_triggers-py-StationTriggerStore-default]]
- [[eos_ai-substrate-station_triggers-py-StationTriggerStore-put]]
- [[eos_ai-substrate-station_triggers-py-_log]]

## Called By

- [[eos_ai-substrate-station_triggers-py-handle_station_trigger]]
