---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 1037
generated: 2026-05-07
---

# is_followup_in_cooldown

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 1037
**Signature:** `is_followup_in_cooldown(summary, now) → bool`

True if a follow-up was emitted within FOLLOW_UP_COOLDOWN_SECONDS.

## Calls

- [[eos_ai-substrate-meeting_intelligence-py-next_followup_eligible_ts]]

## Called By

- [[eos_ai-substrate-meeting_intelligence-py-build_linkage_snapshot]]
- [[eos_ai-substrate-meeting_intelligence-py-detect_follow_up]]
- [[eos_ai-substrate-meeting_intelligence-py-intelligence_report_block]]
