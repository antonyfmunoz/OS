---
type: codebase-function
file: eos_ai/substrate/audio_loop.py
line: 490
generated: 2026-04-11
---

# record_transcript

**File:** [[eos_ai-substrate-audio_loop-py]] | **Line:** 490
**Signature:** `record_transcript(node_id, text) → Optional[TranscriptEntry]`

Append a transcript entry to the node's bounded ring buffer.

Does NOT change status. Callers (e.g. transcript_inject) are expected
to mark_listening / mark_responding explicitly around the call.

## Calls

- [[eos_ai-substrate-audio_loop-py-AudioLoopState-append_transcript]]
- [[eos_ai-substrate-audio_loop-py-AudioLoopStore-get_or_create]]
- [[eos_ai-substrate-audio_loop-py-AudioLoopStore-put]]
- [[eos_ai-substrate-audio_loop-py-_log]]
- [[eos_ai-substrate-audio_loop-py-_new_id]]
- [[eos_ai-substrate-audio_loop-py-_utcnow]]
- [[eos_ai-substrate-audio_loop-py-get_audio_loop_store]]
