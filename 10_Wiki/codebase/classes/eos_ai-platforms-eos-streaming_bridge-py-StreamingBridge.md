---
type: codebase-class
file: eos_ai/platforms/eos/streaming_bridge.py
line: 191
generated: 2026-05-07
---

# StreamingBridge

**File:** [[eos_ai-platforms-eos-streaming_bridge-py]] | **Line:** 191

Singleton event bridge for real-time execution narration.

Accepts events from execution_bridge, pipeline_execution, browser_agent,
and os_controller.  Routes each event to:
1. TTS (non-blocking, interruptible)
...

## Methods

- [[eos_ai-platforms-eos-streaming_bridge-py-StreamingBridge-__init__]]`() → None` — 
- [[eos_ai-platforms-eos-streaming_bridge-py-StreamingBridge-default]]`() → 'StreamingBridge'` — Return the process-wide singleton.
- [[eos_ai-platforms-eos-streaming_bridge-py-StreamingBridge-reset_default_for_tests]]`() → None` — Tear down singleton for test isolation.
- [[eos_ai-platforms-eos-streaming_bridge-py-StreamingBridge-set_session]]`(session_id) → None` — Bind events to a live session.
- [[eos_ai-platforms-eos-streaming_bridge-py-StreamingBridge-set_discord_enabled]]`(enabled) → None` — Toggle Discord forwarding.
- [[eos_ai-platforms-eos-streaming_bridge-py-StreamingBridge-set_tts_enabled]]`(enabled) → None` — Toggle TTS narration.
- [[eos_ai-platforms-eos-streaming_bridge-py-StreamingBridge-subscribe]]`(callback) → None` — Register a callback for all future events.
- [[eos_ai-platforms-eos-streaming_bridge-py-StreamingBridge-unsubscribe]]`(callback) → None` — Remove a previously registered callback.
- [[eos_ai-platforms-eos-streaming_bridge-py-StreamingBridge-stream_event]]`(event_type, message) → StreamEvent` — Emit a streaming event to all outputs.
- [[eos_ai-platforms-eos-streaming_bridge-py-StreamingBridge-_forward_to_discord]]`(event) → None` — Best-effort Discord forwarding.
- [[eos_ai-platforms-eos-streaming_bridge-py-StreamingBridge-cancel_speech]]`() → None` — Cancel current TTS playback immediately.
- [[eos_ai-platforms-eos-streaming_bridge-py-StreamingBridge-is_speaking]]`() → bool` — True if TTS is currently producing audio.
- [[eos_ai-platforms-eos-streaming_bridge-py-StreamingBridge-recent_events]]`(limit) → list[StreamEvent]` — Return the most recent events from the ring buffer.
- [[eos_ai-platforms-eos-streaming_bridge-py-StreamingBridge-events_since]]`(event_id) → list[StreamEvent]` — Return all events after the given event_id.
- [[eos_ai-platforms-eos-streaming_bridge-py-StreamingBridge-clear_history]]`() → None` — Clear the event ring buffer.
