---
type: codebase-function
file: eos_ai/substrate/meeting_sources.py
line: 45
generated: 2026-04-12
---

# is_meeting_source

**File:** [[eos_ai-substrate-meeting_sources-py]] | **Line:** 45
**Signature:** `is_meeting_source(obj) → bool`

Return True if `obj` quacks like a MeetingSourceProtocol.

Cheap structural check — does NOT instantiate, does NOT call read_utterance.

## Called By

- [[eos_ai-substrate-google_meet_source-py-is_google_meet_source]]
- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-attach_source]]
- [[scripts-substrate_google_meet_smoke_test-py-main]]
