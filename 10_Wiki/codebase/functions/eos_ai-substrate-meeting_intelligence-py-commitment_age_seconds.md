---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 962
generated: 2026-04-12
---

# commitment_age_seconds

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 962
**Signature:** `commitment_age_seconds(commitment, now) → float`

Age in seconds of a commitment dict. Safe on bad input.

## Calls

- [[eos_ai-substrate-meeting_intelligence-py-_MeetingSummaryStore-get]]

## Called By

- [[eos_ai-substrate-meeting_intelligence-py-oldest_unresolved_commitment_age_seconds]]
- [[eos_ai-substrate-meeting_intelligence-py-stale_commitments_count]]
