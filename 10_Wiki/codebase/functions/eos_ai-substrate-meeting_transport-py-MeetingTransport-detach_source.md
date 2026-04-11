---
type: codebase-function
file: eos_ai/substrate/meeting_transport.py
line: 323
generated: 2026-04-11
---

# MeetingTransport.detach_source

**File:** [[eos_ai-substrate-meeting_transport-py]] | **Line:** 323
**Signature:** `detach_source(name) → dict[str, Any]`

**Class:** [[eos_ai-substrate-meeting_transport-py-MeetingTransport]]

Detach a previously attached source by name. Never raises.

## Calls

- [[eos_ai-substrate-meeting_sources-py-FakeMeetingSource-close]]
- [[eos_ai-substrate-meeting_sources-py-LiveMeetingSourceStub-close]]
- [[eos_ai-substrate-meeting_sources-py-MeetingSourceProtocol-close]]
- [[eos_ai-substrate-meeting_transport-py-_MeetingTransportHistory-record]]
- [[eos_ai-substrate-meeting_transport-py-_log]]
- [[eos_ai-substrate-meeting_transport-py-get_meeting_transport_history]]

## Called By

- [[scripts-substrate_google_meet_smoke_test-py-main]]
- [[scripts-substrate_meeting_attachment_smoke_test-py-main]]
