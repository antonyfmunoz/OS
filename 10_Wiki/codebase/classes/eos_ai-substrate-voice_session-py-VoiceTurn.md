---
type: codebase-class
file: eos_ai/substrate/voice_session.py
line: 120
generated: 2026-04-11
---

# VoiceTurn

**File:** [[eos_ai-substrate-voice_session-py]] | **Line:** 120

A single bounded turn within a voice session.

`action_id` is set when the turn produced a SPEAK_TEXT SafeAction so
the operator can correlate with ResultStore via result_query.by_action_id.

## Methods

- [[eos_ai-substrate-voice_session-py-VoiceTurn-as_dict]]`() → dict` — 
- [[eos_ai-substrate-voice_session-py-VoiceTurn-from_dict]]`(d) → 'VoiceTurn'` — 

## Decorators

- `@dataclass`
