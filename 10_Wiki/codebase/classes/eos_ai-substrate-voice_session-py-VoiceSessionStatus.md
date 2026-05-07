---
type: codebase-class
file: eos_ai/substrate/voice_session.py
line: 90
generated: 2026-05-07
---

# VoiceSessionStatus

**File:** [[eos_ai-substrate-voice_session-py]] | **Line:** 90

Bounded lifecycle of a single voice session.

PENDING  — created but no turn has happened yet
ACTIVE   — at least one turn has occurred and the session is open
IDLE     — open but no recent activity (left for future timeout sweeps)
...

## Inherits From

- `str`
- `Enum`

## Methods

- [[eos_ai-substrate-voice_session-py-VoiceSessionStatus-is_terminal]]`() → bool` — 
