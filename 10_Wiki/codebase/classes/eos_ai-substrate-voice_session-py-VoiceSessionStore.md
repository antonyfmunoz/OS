---
type: codebase-class
file: eos_ai/substrate/voice_session.py
line: 257
generated: 2026-04-12
---

# VoiceSessionStore

**File:** [[eos_ai-substrate-voice_session-py]] | **Line:** 257

Durable, bounded, thread-safe index of VoiceSessions.

Mirrors ResultStore: dual-layer (in-mem + substrate storage), singleton
via `get_voice_session_store()`. Best-effort persistence — flush failures
log and the in-memory state remains correct.

## Methods

- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-__init__]]`() → None` — 
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-_load]]`() → None` — 
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-_flush]]`() → None` — 
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-_enforce_retention]]`() → None` — 
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-put]]`(session) → None` — 
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-get]]`(session_id) → Optional[VoiceSession]` — 
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-all]]`() → list[VoiceSession]` — 
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-by_node]]`(node_id) → list[VoiceSession]` — 
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-active]]`(node_id) → list[VoiceSession]` — 
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-latest]]`(limit, node_id) → list[VoiceSession]` — 
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-stats]]`() → dict[str, Any]` — 
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-clear]]`() → None` — Test helper. Drops in-memory rows AND the durable payload.
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-__len__]]`() → int` — 
