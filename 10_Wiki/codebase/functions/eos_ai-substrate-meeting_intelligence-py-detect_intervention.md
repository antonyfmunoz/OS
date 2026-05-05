---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 1157
generated: 2026-04-12
---

# detect_intervention

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 1157
**Signature:** `detect_intervention(summary) → Optional[dict]`

Deterministic rule-based trigger. Returns intervention dict or None.

## Calls

- [[eos_ai-substrate-meeting_intelligence-py-_has_repeated_topic]]
- [[eos_ai-substrate-meeting_intelligence-py-_log]]
- [[eos_ai-substrate-meeting_intelligence-py-compute_escalation_level]]
- [[eos_ai-substrate-meeting_intelligence-py-detect_follow_up]]

## Called By

- [[eos_ai-substrate-meeting_intelligence-py-maybe_emit_intervention]]
