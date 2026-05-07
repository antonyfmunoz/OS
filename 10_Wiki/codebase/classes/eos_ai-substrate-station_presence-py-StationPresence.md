---
type: codebase-class
file: eos_ai/substrate/station_presence.py
line: 77
generated: 2026-05-07
---

# StationPresence

**File:** [[eos_ai-substrate-station_presence-py]] | **Line:** 77

Unified station presence snapshot.

Aggregates posture mode, node availability, and wake/clap/tts flags
into a single persistent object.

## Methods

- [[eos_ai-substrate-station_presence-py-StationPresence-new]]`() → StationPresence` — Create a fresh default presence.
- [[eos_ai-substrate-station_presence-py-StationPresence-to_dict]]`() → dict` — Serialize to a plain dict suitable for JSON storage.
- [[eos_ai-substrate-station_presence-py-StationPresence-from_dict]]`(d) → StationPresence` — Deserialize from a plain dict.  Tolerant of missing/bad keys.

## Decorators

- `@dataclass`
