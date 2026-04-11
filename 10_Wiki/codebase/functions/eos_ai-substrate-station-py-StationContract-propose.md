---
type: codebase-function
file: eos_ai/substrate/station.py
line: 176
generated: 2026-04-11
---

# StationContract.propose

**File:** [[eos_ai-substrate-station-py]] | **Line:** 176
**Signature:** `propose(action) → SafeAction`

**Class:** [[eos_ai-substrate-station-py-StationContract]]

Register an action for transmission to the station.

Enforces two gates in order:
  1. Control mode: OBSERVE rejects everything.
  2. MVP allow-list: only MVP_ALLOWED_ACTIONS pass in this phase.
...

## Called By

- [[eos_ai-substrate-station_helpers-py-propose_focus_app]]
- [[eos_ai-substrate-station_helpers-py-propose_launch_app]]
- [[eos_ai-substrate-station_helpers-py-propose_open_scene]]
- [[eos_ai-substrate-station_helpers-py-propose_open_url]]
- [[eos_ai-substrate-station_helpers-py-propose_play_sound]]
- [[eos_ai-substrate-station_helpers-py-propose_speak_text]]
