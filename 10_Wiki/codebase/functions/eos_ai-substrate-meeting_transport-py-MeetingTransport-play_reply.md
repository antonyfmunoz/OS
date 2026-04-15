---
type: codebase-function
file: eos_ai/substrate/meeting_transport.py
line: 458
generated: 2026-04-12
---

# MeetingTransport.play_reply

**File:** [[eos_ai-substrate-meeting_transport-py]] | **Line:** 458
**Signature:** `play_reply(text) → dict[str, Any]`

**Class:** [[eos_ai-substrate-meeting_transport-py-MeetingTransport]]

Bounded playback entry point for an EOS reply.

Always returns a JSON-friendly dict. If no sink is attached or
playback is disabled, returns a structured `disabled` result instead
of raising.

## Calls

- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-_record_playback]]

## Called By

- [[eos_ai-substrate-meeting_transport-py-MeetingTransport-inject_utterance]]
- [[scripts-substrate_meeting_transport_smoke_test-py-main]]
