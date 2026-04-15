---
type: codebase-function
file: eos_ai/substrate/meeting_transport.py
line: 271
generated: 2026-04-12
---

# MeetingTransport.attach_source

**File:** [[eos_ai-substrate-meeting_transport-py]] | **Line:** 271
**Signature:** `attach_source(source) → dict[str, Any]`

**Class:** [[eos_ai-substrate-meeting_transport-py-MeetingTransport]]

Attach a meeting transcript source (duck-typed MeetingSourceProtocol).

The source is a PULL producer — call ``pump_attached_sources()`` to
drain it through the bounded inject_utterance seam. Push-style
bridges may continue to call ``inject_utterance`` directly; this
...

## Calls

- [[eos_ai-substrate-meeting_sources-py-is_meeting_source]]
- [[eos_ai-substrate-meeting_transport-py-_MeetingTransportHistory-record]]
- [[eos_ai-substrate-meeting_transport-py-_utcnow_iso]]
- [[eos_ai-substrate-meeting_transport-py-get_meeting_transport_history]]

## Called By

- [[scripts-substrate_google_meet_smoke_test-py-main]]
- [[scripts-substrate_meeting_attachment_smoke_test-py-main]]
