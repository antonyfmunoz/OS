---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 911
generated: 2026-05-07
---

# ownership_pressure_hint

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 911
**Signature:** `ownership_pressure_hint(summary) → str`

Single bounded label describing ownership health of unresolved commitments.
  - "clear"    → unresolved items all have owners
  - "diffused" → mix of owned + unowned
  - "missing"  → all unresolved items are unowned
  - "clear"    → no unresolved items (default calm state)

## Calls

- [[eos_ai-substrate-meeting_intelligence-py-_MeetingSummaryStore-get]]
- [[eos_ai-substrate-meeting_intelligence-py-unresolved_commitments]]

## Called By

- [[eos_ai-substrate-meeting_intelligence-py-build_linkage_snapshot]]
- [[eos_ai-substrate-meeting_intelligence-py-detect_follow_up]]
- [[eos_ai-substrate-meeting_intelligence-py-intelligence_report_block]]
