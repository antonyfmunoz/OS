---
type: codebase-class
file: eos_ai/substrate/voice_session.py
line: 154
generated: 2026-04-12
---

# VoiceSession

**File:** [[eos_ai-substrate-voice_session-py]] | **Line:** 154

A bounded live voice interaction container.

Embeds turns directly so the row is a single atomic upsert. Capped per
session by `_MAX_TURNS_PER_SESSION`; oldest turns drop on overflow.

## Methods

- [[eos_ai-substrate-voice_session-py-VoiceSession-turn_count]]`() → int` — 
- [[eos_ai-substrate-voice_session-py-VoiceSession-last_turn]]`() → Optional[VoiceTurn]` — 
- [[eos_ai-substrate-voice_session-py-VoiceSession-append_turn]]`(turn) → None` — 
- [[eos_ai-substrate-voice_session-py-VoiceSession-record_role_switch]]`(from_slug, to_slug) → None` — 
- [[eos_ai-substrate-voice_session-py-VoiceSession-as_dict]]`() → dict` — 
- [[eos_ai-substrate-voice_session-py-VoiceSession-from_dict]]`(d) → 'VoiceSession'` — 

## Decorators

- `@dataclass`
