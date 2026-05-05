---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 688
generated: 2026-04-12
---

# extract_commitments

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 688
**Signature:** `extract_commitments(utterances) → list[Commitment]`

Deterministic v1 commitment extraction.

Scans utterances for simple trigger phrases ("I will", "follow up", etc.)
and emits Commitment objects. Never raises; returns bounded list.

## Calls

- [[eos_ai-substrate-meeting_intelligence-py-_MeetingSummaryStore-get]]
- [[eos_ai-substrate-meeting_intelligence-py-_infer_ownership]]
- [[eos_ai-substrate-meeting_intelligence-py-_log]]

## Called By

- [[eos_ai-substrate-meeting_intelligence-py-update_meeting_summary]]
