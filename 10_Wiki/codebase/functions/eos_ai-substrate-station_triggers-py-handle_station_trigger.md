---
type: codebase-function
file: eos_ai/substrate/station_triggers.py
line: 269
generated: 2026-05-07
---

# handle_station_trigger

**File:** [[eos_ai-substrate-station_triggers-py]] | **Line:** 269
**Signature:** `handle_station_trigger(trigger_type, phrase) → dict[str, Any]`

Handle a trigger by dispatching to the appropriate control-plane flow.

Rules for v1:
- Triggers call control-plane workflows only.
- Supported actions: open_day, open_scene, activate_station.
...

## Calls

- [[eos_ai-substrate-station_triggers-py-StationTriggerStore-default]]
- [[eos_ai-substrate-station_triggers-py-_log]]
- [[eos_ai-substrate-station_triggers-py-register_station_trigger]]
