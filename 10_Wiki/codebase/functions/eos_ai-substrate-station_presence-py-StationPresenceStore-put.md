---
type: codebase-function
file: eos_ai/substrate/station_presence.py
line: 195
generated: 2026-05-07
---

# StationPresenceStore.put

**File:** [[eos_ai-substrate-station_presence-py]] | **Line:** 195
**Signature:** `put(state) → None`

**Class:** [[eos_ai-substrate-station_presence-py-StationPresenceStore]]

Update the state, stamp updated_at, and persist.

## Calls

- [[eos_ai-substrate-station_presence-py-StationPresenceStore-_flush]]
- [[eos_ai-substrate-station_presence-py-_utcnow]]

## Called By

- [[eos_ai-substrate-station_presence-py-StationPresenceStore-_flush]]
- [[eos_ai-substrate-station_presence-py-update_station_presence]]
