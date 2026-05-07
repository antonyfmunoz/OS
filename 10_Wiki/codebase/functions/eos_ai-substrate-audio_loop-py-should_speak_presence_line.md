---
type: codebase-function
file: eos_ai/substrate/audio_loop.py
line: 522
generated: 2026-05-07
---

# should_speak_presence_line

**File:** [[eos_ai-substrate-audio_loop-py]] | **Line:** 522
**Signature:** `should_speak_presence_line(node_id) → bool`

Dedupe logic for operator_presence spoken lines.

Returns True if the (from_mode, to_mode) line for this node has NOT
been spoken within the last `cooldown_s` seconds. The key combines
both modes so a legitimate later transition is still allowed.

## Calls

- [[eos_ai-substrate-audio_loop-py-AudioLoopStore-get]]
- [[eos_ai-substrate-audio_loop-py-_log]]
- [[eos_ai-substrate-audio_loop-py-_parse_iso]]
- [[eos_ai-substrate-audio_loop-py-get_audio_loop_store]]
