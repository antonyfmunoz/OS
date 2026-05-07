---
type: codebase-function
file: eos_ai/voice_interface.py
line: 260
generated: 2026-05-07
---

# VoiceInterface.process_voice_turn

**File:** [[eos_ai-voice_interface-py]] | **Line:** 260
**Signature:** `process_voice_turn(audio_path, agent, venture_id) → dict`

**Class:** [[eos_ai-voice_interface-py-VoiceInterface]]

Full voice conversation turn:
  1. transcribe(audio_path) → text
  2. Route text through CognitiveLoop
  3. synthesize response audio
  4. Log to session transcript
...

## Calls

- [[eos_ai-voice_interface-py-VoiceInterface-synthesize]]
- [[eos_ai-voice_interface-py-VoiceInterface-transcribe]]
