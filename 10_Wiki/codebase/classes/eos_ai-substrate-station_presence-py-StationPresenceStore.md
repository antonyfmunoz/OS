---
type: codebase-class
file: eos_ai/substrate/station_presence.py
line: 140
generated: 2026-05-07
---

# StationPresenceStore

**File:** [[eos_ai-substrate-station_presence-py]] | **Line:** 140

Durable, thread-safe singleton store for StationPresence.

Stores a SINGLE StationPresence (not a collection) under the
``station_presence`` key in substrate storage.  Dual-layer: in-memory
for speed, flushed to durable storage on every mutation.

## Methods

- [[eos_ai-substrate-station_presence-py-StationPresenceStore-__init__]]`() → None` — 
- [[eos_ai-substrate-station_presence-py-StationPresenceStore-_load]]`() → None` — 
- [[eos_ai-substrate-station_presence-py-StationPresenceStore-_flush]]`() → None` — 
- [[eos_ai-substrate-station_presence-py-StationPresenceStore-get]]`() → StationPresence` — Return current state, creating a default if none exists.
- [[eos_ai-substrate-station_presence-py-StationPresenceStore-put]]`(state) → None` — Update the state, stamp updated_at, and persist.
- [[eos_ai-substrate-station_presence-py-StationPresenceStore-default]]`() → StationPresenceStore` — Return the process-wide singleton store.
- [[eos_ai-substrate-station_presence-py-StationPresenceStore-reset_default_for_tests]]`() → None` — Test hook — drop the singleton so the next default() re-resolves.
