---
type: codebase-function
file: eos_ai/platforms/eos/streaming_bridge.py
line: 263
generated: 2026-05-07
---

# StreamingBridge.stream_event

**File:** [[eos_ai-platforms-eos-streaming_bridge-py]] | **Line:** 263
**Signature:** `stream_event(event_type, message) → StreamEvent`

**Class:** [[eos_ai-platforms-eos-streaming_bridge-py-StreamingBridge]]

Emit a streaming event to all outputs.

Args:
    event_type: Category of the event.
    message: Human-readable narration text.
...

## Calls

- [[eos_ai-platforms-eos-streaming_bridge-py-StreamingBridge-_forward_to_discord]]
- [[eos_ai-platforms-eos-streaming_bridge-py-_TTSEngine-speak]]
- [[eos_ai-platforms-eos-streaming_bridge-py-_log]]
- [[eos_ai-platforms-eos-streaming_bridge-py-_new_id]]

## Called By

- [[eos_ai-platforms-eos-streaming_bridge-py-stream_event]]
