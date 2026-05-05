---
type: codebase-function
file: eos_ai/substrate/transcript_inject.py
line: 71
generated: 2026-04-12
---

# inject_transcript

**File:** [[eos_ai-substrate-transcript_inject-py]] | **Line:** 71
**Signature:** `inject_transcript(node_id, text) → dict[str, Any]`

Bounded entry point for transcript-shaped input into the voice loop.

Returns a JSON-friendly dict with keys:
    status:        "ok" | "empty_text" | "no_active_session" |
                   "start_failed" | "submit_failed" | "session_terminal"
...

## Calls

- [[eos_ai-substrate-transcript_inject-py-_log]]
- [[eos_ai-substrate-transcript_inject-py-_resolve_active_session_id]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionRuntime-start_session]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionRuntime-submit_utterance]]
- [[eos_ai-substrate-voice_session-py-VoiceSessionStore-get]]
- [[eos_ai-substrate-voice_session-py-_log]]
- [[eos_ai-substrate-voice_session-py-get_voice_session_store]]

## Called By

- [[scripts-substrate_audio_loop_smoke_test-py-main]]
