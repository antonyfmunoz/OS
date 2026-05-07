---
type: codebase-function
file: eos_ai/platforms/eos/live_runtime.py
line: 322
generated: 2026-05-07
---

# EALiveRuntime.handle_utterance

**File:** [[eos_ai-platforms-eos-live_runtime-py]] | **Line:** 322
**Signature:** `handle_utterance(text) → LiveRuntimeResult`

**Class:** [[eos_ai-platforms-eos-live_runtime-py-EALiveRuntime]]

Process a founder utterance through the live runtime.

Flow:
1. Classify control phrase — if match, route to handler immediately.
2. If STOPPED, return stop message.
...

## Calls

- [[eos_ai-platforms-eos-live_runtime-py-EALiveRuntime-_attach_work_to_session]]
- [[eos_ai-platforms-eos-live_runtime-py-EALiveRuntime-_bind_streaming_bridge]]
- [[eos_ai-platforms-eos-live_runtime-py-EALiveRuntime-_ensure_live_session]]
- [[eos_ai-platforms-eos-live_runtime-py-EALiveRuntime-_handle_pause]]
- [[eos_ai-platforms-eos-live_runtime-py-EALiveRuntime-_handle_resume]]
- [[eos_ai-platforms-eos-live_runtime-py-EALiveRuntime-_handle_stop]]
- [[eos_ai-platforms-eos-live_runtime-py-EALiveRuntime-_stream_state_change]]
- [[eos_ai-platforms-eos-live_runtime-py-_classify_control_phrase]]
- [[eos_ai-platforms-eos-live_runtime-py-_log]]
- [[eos_ai-platforms-eos-live_runtime-py-_utcnow]]

## Called By

- [[eos_ai-platforms-eos-live_runtime-py-handle_live_user_utterance]]
- [[eos_ai-platforms-eos-live_runtime-py-interrupt_live_runtime]]
