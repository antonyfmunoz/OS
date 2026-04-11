---
type: codebase-function
file: eos_ai/voice_engine.py
line: 544
generated: 2026-04-11
---

# VoiceEngine.query_local

**File:** [[eos_ai-voice_engine-py]] | **Line:** 544
**Signature:** `query_local(prompt, system) → str`

**Class:** [[eos_ai-voice_engine-py-VoiceEngine]]

Query Qwen2.5:7b locally via Ollama.

Free and fast — no Anthropic API cost. Use for simple/quick queries.
Returns empty string if Ollama is not running.

## Called By

- [[eos_ai-voice_engine-py-VoiceEngine-route_query]]
