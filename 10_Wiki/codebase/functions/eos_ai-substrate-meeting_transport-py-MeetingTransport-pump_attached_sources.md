---
type: codebase-function
file: eos_ai/substrate/meeting_transport.py
line: 366
generated: 2026-04-12
---

# MeetingTransport.pump_attached_sources

**File:** [[eos_ai-substrate-meeting_transport-py]] | **Line:** 366
**Signature:** `pump_attached_sources() → dict[str, Any]`

**Class:** [[eos_ai-substrate-meeting_transport-py-MeetingTransport]]

Drain up to ``max_per_source`` utterances from each attached source.

Each utterance is routed through ``self.inject_utterance``, tagged
with ``meeting_source`` and ``meeting_provider`` metadata. Per-source
exceptions are caught and recorded — pump never raises.

## Calls

- [[eos_ai-substrate-meeting_sources-py-FakeMeetingSource-read_utterance]]
- [[eos_ai-substrate-meeting_sources-py-LiveMeetingSourceStub-read_utterance]]
- [[eos_ai-substrate-meeting_sources-py-MeetingSourceProtocol-read_utterance]]
- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-inject_utterance]]
- [[eos_ai-substrate-meeting_transport-py-_utcnow_iso]]

## Called By

- [[scripts-substrate_google_meet_smoke_test-py-main]]
- [[scripts-substrate_meeting_attachment_smoke_test-py-main]]
