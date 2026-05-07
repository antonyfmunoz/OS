---
type: codebase-class
file: eos_ai/substrate/station.py
line: 96
generated: 2026-05-07
---

# StationEvent

**File:** [[eos_ai-substrate-station-py]] | **Line:** 96

Out-of-band event the station wants EOS to know about.

Examples: user started a pomodoro, user plugged in headphones, user opened
Notion, listener transcribed a phrase. These are *facts*, not requests.
EOS may react via cognitive_loop but the station does not assume it will.

## Decorators

- `@dataclass`
