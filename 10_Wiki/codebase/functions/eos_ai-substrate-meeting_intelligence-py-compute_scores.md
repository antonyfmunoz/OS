---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 602
generated: 2026-04-11
---

# compute_scores

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 602
**Signature:** `compute_scores(summary) → None`

Deterministically compute decision_pressure_score, ambiguity_score,
priority_level on a MeetingSummary in-place. Never raises.

## Calls

- [[eos_ai-substrate-meeting_intelligence-py-_MeetingSummaryStore-get]]
- [[eos_ai-substrate-meeting_intelligence-py-_count_ambiguity_overlaps]]
- [[eos_ai-substrate-meeting_intelligence-py-_log]]
- [[eos_ai-substrate-meeting_intelligence-py-unresolved_commitments]]

## Called By

- [[eos_ai-substrate-meeting_intelligence-py-update_meeting_summary]]
