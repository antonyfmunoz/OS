---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 934
generated: 2026-05-07
---

# compute_escalation_level

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 934
**Signature:** `compute_escalation_level(summary) → str`

Derive escalation from existing scores + unresolved commitment count.
Deterministic. Never raises. Writes to summary.escalation_level and returns it.

## Calls

- [[eos_ai-substrate-meeting_intelligence-py-_log]]
- [[eos_ai-substrate-meeting_intelligence-py-unresolved_commitments]]

## Called By

- [[eos_ai-substrate-meeting_intelligence-py-detect_intervention]]
- [[eos_ai-substrate-meeting_intelligence-py-update_meeting_summary]]
