---
type: codebase-function
file: eos_ai/substrate/meeting_transport.py
line: 962
generated: 2026-05-07
---

# maybe_mirror_meeting_utterance

**File:** [[eos_ai-substrate-meeting_transport-py]] | **Line:** 962
**Signature:** `maybe_mirror_meeting_utterance(text) → Optional[dict[str, Any]]`

Opt-in mirror hook for an external meeting bridge.

Behavior:
  - Returns ``None`` immediately if EOS_MEETING_VOICE_TRANSPORT_ENABLED
    is not truthy. This is the DEFAULT — no behavior change anywhere
...

## Calls

- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-inject_utterance]]
- [[eos_ai-substrate-meeting_transport-py-_env_hook_enabled]]
- [[eos_ai-substrate-meeting_transport-py-_log]]
- [[eos_ai-substrate-meeting_transport-py-get_default_meeting_transport]]

## Called By

- [[scripts-substrate_meeting_transport_smoke_test-py-main]]
