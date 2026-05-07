---
type: codebase-function
file: eos_ai/substrate/station_presence.py
line: 280
generated: 2026-05-07
---

# get_station_summary

**File:** [[eos_ai-substrate-station_presence-py]] | **Line:** 280
**Signature:** `get_station_summary() → dict`

Get unified station summary for open_day/close_day integration.

Reads from station_presence for posture, and best-effort reads
from local_control for control_mode.

...

## Calls

- [[eos_ai-substrate-station_presence-py-StationPresenceStore-default]]
- [[eos_ai-substrate-station_presence-py-get_station_presence]]
