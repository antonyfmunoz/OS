---
type: codebase-class
file: eos_ai/platforms/eos/voice_runtime.py
line: 253
generated: 2026-05-07
---

# VoiceRuntime

**File:** [[eos_ai-platforms-eos-voice_runtime-py]] | **Line:** 253

Continuous conversational voice loop.

Singleton via default().  Runs the listen→transcribe→process→speak
loop in a dedicated daemon thread.  Thread-safe.

## Methods

- [[eos_ai-platforms-eos-voice_runtime-py-VoiceRuntime-__init__]]`() → None` — 
- [[eos_ai-platforms-eos-voice_runtime-py-VoiceRuntime-default]]`() → 'VoiceRuntime'` — Return the process-wide singleton.
- [[eos_ai-platforms-eos-voice_runtime-py-VoiceRuntime-reset_default_for_tests]]`() → None` — Tear down singleton for test isolation.
- [[eos_ai-platforms-eos-voice_runtime-py-VoiceRuntime-configure]]`() → None` — Update runtime configuration.  Can be called while running.
- [[eos_ai-platforms-eos-voice_runtime-py-VoiceRuntime-on_utterance]]`(callback) → None` — Register callback for when user speech is transcribed.
- [[eos_ai-platforms-eos-voice_runtime-py-VoiceRuntime-on_response]]`(callback) → None` — Register callback for when EA responds.
- [[eos_ai-platforms-eos-voice_runtime-py-VoiceRuntime-start]]`() → None` — Start the voice loop in a background thread.
- [[eos_ai-platforms-eos-voice_runtime-py-VoiceRuntime-stop]]`() → None` — Stop the voice loop.
- [[eos_ai-platforms-eos-voice_runtime-py-VoiceRuntime-is_running]]`() → bool` — True if the voice loop is active.
- [[eos_ai-platforms-eos-voice_runtime-py-VoiceRuntime-state]]`() → VoiceRuntimeState` — Current observable state.
- [[eos_ai-platforms-eos-voice_runtime-py-VoiceRuntime-interrupt]]`(new_text) → None` — Interrupt current activity.
- [[eos_ai-platforms-eos-voice_runtime-py-VoiceRuntime-_voice_loop]]`() → None` — Main voice loop.  Runs in background thread.
- [[eos_ai-platforms-eos-voice_runtime-py-VoiceRuntime-_single_cycle]]`() → None` — Execute one listen→transcribe→process→speak cycle.
- [[eos_ai-platforms-eos-voice_runtime-py-VoiceRuntime-_wait_for_wake_word]]`() → bool` — Listen for the wake phrase.  Returns True when detected.
- [[eos_ai-platforms-eos-voice_runtime-py-VoiceRuntime-_listen_until_silence]]`() → list[bytes]` — Accumulate audio chunks until silence is detected.
- [[eos_ai-platforms-eos-voice_runtime-py-VoiceRuntime-_process_utterance]]`(text) → None` — Route transcribed text through live_runtime and speak the response.
