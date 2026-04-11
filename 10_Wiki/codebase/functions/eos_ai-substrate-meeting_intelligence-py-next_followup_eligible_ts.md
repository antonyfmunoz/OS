---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 1022
generated: 2026-04-11
---

# next_followup_eligible_ts

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 1022
**Signature:** `next_followup_eligible_ts(summary) → Optional[float]`

Earliest wall-clock timestamp a new follow-up prompt may be emitted.
Uses last_followup_prompt_ts (or last_followup_ts as fallback) + cooldown.
Returns None if no follow-up has ever been emitted.

## Called By

- [[eos_ai-substrate-meeting_intelligence-py-build_linkage_snapshot]]
- [[eos_ai-substrate-meeting_intelligence-py-intelligence_report_block]]
- [[eos_ai-substrate-meeting_intelligence-py-is_followup_in_cooldown]]
