---
type: codebase-function
file: eos_ai/substrate/meeting_transport.py
line: 897
generated: 2026-05-07
---

# get_default_meeting_transport

**File:** [[eos_ai-substrate-meeting_transport-py]] | **Line:** 897
**Signature:** `get_default_meeting_transport() → MeetingTransport`

Return (or lazily create) a default transport for (platform, meeting_id).

The adapter is intentionally cheap to construct, but operators usually
want one stable instance per meeting for transport history coherence.

## Calls

- [[eos_ai-substrate-meeting_transport-py-_normalize_platform]]

## Called By

- [[eos_ai-substrate-meeting_transport-py-maybe_mirror_meeting_utterance]]
- [[scripts-substrate_meeting_transport_smoke_test-py-main]]
