---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 2098
generated: 2026-05-07
---

# linkage_snapshot

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 2098
**Signature:** `linkage_snapshot(node_id, meeting_id) → dict[str, Any]`

Product-facing entry point: fetch the live summary and return a stable,
versioned Product Linkage snapshot. Never raises; degrades safely.

## Calls

- [[eos_ai-substrate-meeting_intelligence-py-_MeetingSummaryStore-get]]
- [[eos_ai-substrate-meeting_intelligence-py-_empty_linkage_snapshot]]
- [[eos_ai-substrate-meeting_intelligence-py-_log]]
- [[eos_ai-substrate-meeting_intelligence-py-build_linkage_snapshot]]
- [[eos_ai-substrate-meeting_intelligence-py-get_meeting_summary_store]]

## Called By

- [[eos_ai-substrate-meeting_intelligence-py-product_linkage_block]]
