---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 767
generated: 2026-04-12
---

# resolve_commitments

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 767
**Signature:** `resolve_commitments(summary, utterances) → list[dict]`

Deterministic v1 resolution detection.

Scans new utterances for simple resolution phrases and matches them
against unresolved commitments via keyword overlap. On match the
commitment dict is mutated in-place (resolved=True, resolved_at=now)
...

## Calls

- [[eos_ai-substrate-meeting_intelligence-py-_MeetingSummaryStore-get]]
- [[eos_ai-substrate-meeting_intelligence-py-_log]]
- [[eos_ai-substrate-meeting_intelligence-py-_tokens]]

## Called By

- [[eos_ai-substrate-meeting_intelligence-py-update_meeting_summary]]
