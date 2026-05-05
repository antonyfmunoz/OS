---
type: codebase-function
file: eos_ai/substrate/meeting_transport.py
line: 235
generated: 2026-04-12
---

# MeetingTransport.attach_playback_sink

**File:** [[eos_ai-substrate-meeting_transport-py]] | **Line:** 235
**Signature:** `attach_playback_sink(sink) → dict[str, Any]`

**Class:** [[eos_ai-substrate-meeting_transport-py-MeetingTransport]]

Attach a bounded playback/egress sink.

The sink contract is intentionally minimal: an object exposing
``play_text(text: str) -> Any``. A future real meeting bridge can
plug a TTS-into-meeting sink here without touching the seam. Until
...

## Calls

- [[eos_ai-substrate-meeting_transport-py-_log]]

## Called By

- [[scripts-substrate_meeting_transport_smoke_test-py-main]]
