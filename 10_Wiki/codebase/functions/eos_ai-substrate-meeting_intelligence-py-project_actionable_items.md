---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 1487
generated: 2026-04-12
---

# project_actionable_items

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 1487
**Signature:** `project_actionable_items(summary) → list[ActionableItem]`

Turn an existing MeetingSummary into a bounded list of ActionableItem
projections. Pure function; never mutates the summary. Never raises.

Sources (in order, bounded by MAX_ACTIONABLE_ITEMS):
  1. Unresolved commitments     → kind="commitment"
...

## Calls

- [[eos_ai-substrate-meeting_intelligence-py-_MeetingSummaryStore-get]]
- [[eos_ai-substrate-meeting_intelligence-py-_decision_implies_followup]]
- [[eos_ai-substrate-meeting_intelligence-py-_log]]
- [[eos_ai-substrate-meeting_intelligence-py-classify_execution_readiness]]
- [[eos_ai-substrate-meeting_intelligence-py-stale_open_loops_count]]
- [[eos_ai-substrate-meeting_intelligence-py-unresolved_commitments]]

## Called By

- [[eos_ai-substrate-meeting_intelligence-py-execution_linkage_block]]
