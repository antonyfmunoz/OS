---
type: codebase-class
file: eos_ai/substrate/live_sessions.py
line: 59
generated: 2026-05-07
---

# LiveSessionState

**File:** [[eos_ai-substrate-live_sessions-py]] | **Line:** 59

Bounded lifecycle of a live session.

CREATED              — allocated but not yet active
ACTIVE               — live interaction in progress
PAUSED               — temporarily suspended (break, context switch)
...

## Inherits From

- `str`
- `Enum`
