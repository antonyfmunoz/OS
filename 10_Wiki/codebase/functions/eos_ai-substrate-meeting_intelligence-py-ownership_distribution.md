---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 879
generated: 2026-04-11
---

# ownership_distribution

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 879
**Signature:** `ownership_distribution(summary) → dict[str, int]`

Bounded count of commitments per owner label. Unowned commitments are
NOT included here (use unassigned_commitments_count). Cap enforced.

## Calls

- [[eos_ai-substrate-meeting_intelligence-py-_MeetingSummaryStore-get]]
- [[eos_ai-substrate-meeting_intelligence-py-_log]]

## Called By

- [[eos_ai-substrate-meeting_intelligence-py-build_linkage_snapshot]]
- [[eos_ai-substrate-meeting_intelligence-py-intelligence_report_block]]
