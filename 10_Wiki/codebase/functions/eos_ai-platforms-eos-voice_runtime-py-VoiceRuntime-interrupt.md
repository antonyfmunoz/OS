---
type: codebase-function
file: eos_ai/platforms/eos/voice_runtime.py
line: 387
generated: 2026-05-07
---

# VoiceRuntime.interrupt

**File:** [[eos_ai-platforms-eos-voice_runtime-py]] | **Line:** 387
**Signature:** `interrupt(new_text) → None`

**Class:** [[eos_ai-platforms-eos-voice_runtime-py-VoiceRuntime]]

Interrupt current activity.

If new_text is provided, it's processed as a new utterance.
Otherwise just cancels current TTS.

## Calls

- [[eos_ai-platforms-eos-voice_runtime-py-VoiceRuntime-_process_utterance]]

## Called By

- [[eos_ai-platforms-eos-voice_runtime-py-interrupt_voice_runtime]]
