---
type: codebase-function
file: eos_ai/substrate/meeting_transport.py
line: 693
generated: 2026-04-12
---

# MeetingTransport.inject_utterance

**File:** [[eos_ai-substrate-meeting_transport-py]] | **Line:** 693
**Signature:** `inject_utterance(text) → dict[str, Any]`

**Class:** [[eos_ai-substrate-meeting_transport-py-MeetingTransport]]

Bounded entry point. Mirrors transcript_inject.inject_transcript()
with `source="meeting_voice"` and meeting-shaped metadata.

Never raises. Always returns a JSON-friendly dict.

## Calls

- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-_latest_agent_reply]]
- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-play_reply]]
- [[eos_ai-substrate-meeting_transport-py-MeetingTransportEvent-as_dict]]
- [[eos_ai-substrate-meeting_transport-py-_MeetingTransportHistory-record]]
- [[eos_ai-substrate-meeting_transport-py-get_meeting_transport_history]]

## Called By

- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-pump_attached_sources]]
- [[eos_ai-substrate-meeting_transport-py-maybe_mirror_meeting_utterance]]
- [[scripts-substrate_google_meet_smoke_test-py-main]]
- [[scripts-substrate_meeting_transport_smoke_test-py-main]]
