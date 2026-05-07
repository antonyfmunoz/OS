---
type: codebase-class
file: eos_ai/platforms/eos/streaming_bridge.py
line: 93
generated: 2026-05-07
---

# _TTSEngine

**File:** [[eos_ai-platforms-eos-streaming_bridge-py]] | **Line:** 93

Non-blocking, interruptible TTS wrapper.

Uses pyttsx3 (local) with espeak fallback.  Speech runs in a
background thread so callers never block.

## Methods

- [[eos_ai-platforms-eos-streaming_bridge-py-_TTSEngine-__init__]]`() → None` — 
- [[eos_ai-platforms-eos-streaming_bridge-py-_TTSEngine-_ensure_engine]]`() → bool` — Lazily init pyttsx3.  Returns True if ready.
- [[eos_ai-platforms-eos-streaming_bridge-py-_TTSEngine-speak]]`(text) → None` — Speak text in a background thread.  Non-blocking.
- [[eos_ai-platforms-eos-streaming_bridge-py-_TTSEngine-_speak_espeak]]`(text) → None` — Fallback: use espeak subprocess.
- [[eos_ai-platforms-eos-streaming_bridge-py-_TTSEngine-cancel]]`() → None` — Cancel current speech immediately.
- [[eos_ai-platforms-eos-streaming_bridge-py-_TTSEngine-is_speaking]]`() → bool` — True if TTS is currently producing audio.
