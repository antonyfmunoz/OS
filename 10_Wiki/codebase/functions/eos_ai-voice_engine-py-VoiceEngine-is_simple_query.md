---
type: codebase-function
file: eos_ai/voice_engine.py
line: 587
generated: 2026-04-12
---

# VoiceEngine.is_simple_query

**File:** [[eos_ai-voice_engine-py]] | **Line:** 587
**Signature:** `is_simple_query(text) → bool`

**Class:** [[eos_ai-voice_engine-py-VoiceEngine]]

Determine if query can be handled locally (Ollama) vs Claude (EOS).

## Called By

- [[eos_ai-voice_engine-py-VoiceEngine-route_query]]
- [[services-discord_bot-py-_listen_loop]]
