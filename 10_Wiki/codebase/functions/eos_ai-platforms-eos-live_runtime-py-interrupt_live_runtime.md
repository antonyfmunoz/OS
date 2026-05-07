---
type: codebase-function
file: eos_ai/platforms/eos/live_runtime.py
line: 483
generated: 2026-05-07
---

# interrupt_live_runtime

**File:** [[eos_ai-platforms-eos-live_runtime-py]] | **Line:** 483
**Signature:** `interrupt_live_runtime(new_text) → LiveRuntimeResult`

Interrupt the current activity and handle new text.

If the runtime is EXECUTING or SPEAKING, transitions to LISTENING first.
Then processes the new utterance.

## Calls

- [[eos_ai-platforms-eos-live_runtime-py-EALiveRuntime-default]]
- [[eos_ai-platforms-eos-live_runtime-py-EALiveRuntime-handle_utterance]]
- [[eos_ai-platforms-eos-live_runtime-py-_log]]
- [[eos_ai-platforms-eos-live_runtime-py-_utcnow]]
