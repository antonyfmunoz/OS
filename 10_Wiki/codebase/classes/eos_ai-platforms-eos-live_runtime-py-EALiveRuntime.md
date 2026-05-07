---
type: codebase-class
file: eos_ai/platforms/eos/live_runtime.py
line: 119
generated: 2026-05-07
---

# EALiveRuntime

**File:** [[eos_ai-platforms-eos-live_runtime-py]] | **Line:** 119

Singleton conversational state machine for EA live interaction.

Tracks runtime state, current work items, and the bound live session.
All founder utterances flow through handle_utterance().

## Methods

- [[eos_ai-platforms-eos-live_runtime-py-EALiveRuntime-default]]`() → 'EALiveRuntime'` — Return the process-level singleton.
- [[eos_ai-platforms-eos-live_runtime-py-EALiveRuntime-reset_default_for_tests]]`() → None` — Tear down the singleton for test isolation.
- [[eos_ai-platforms-eos-live_runtime-py-EALiveRuntime-_ensure_live_session]]`() → None` — Create or verify the bound live session.
- [[eos_ai-platforms-eos-live_runtime-py-EALiveRuntime-_attach_work_to_session]]`(task_ids, pipeline_ids) → None` — Attach tasks and pipelines to the current live session.
- [[eos_ai-platforms-eos-live_runtime-py-EALiveRuntime-_bind_streaming_bridge]]`() → None` — Bind the streaming bridge to the current live session.
- [[eos_ai-platforms-eos-live_runtime-py-EALiveRuntime-_stream_state_change]]`(message) → None` — Emit a streaming event for runtime state transitions.
- [[eos_ai-platforms-eos-live_runtime-py-EALiveRuntime-_handle_pause]]`() → LiveRuntimeResult` — Pause the runtime and the bound live session.
- [[eos_ai-platforms-eos-live_runtime-py-EALiveRuntime-_handle_stop]]`() → LiveRuntimeResult` — Stop the runtime and end the live session.
- [[eos_ai-platforms-eos-live_runtime-py-EALiveRuntime-_handle_resume]]`() → LiveRuntimeResult` — Resume the runtime, the live session, and any paused pipelines.
- [[eos_ai-platforms-eos-live_runtime-py-EALiveRuntime-handle_utterance]]`(text) → LiveRuntimeResult` — Process a founder utterance through the live runtime.

## Decorators

- `@dataclass`
