---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 1072
generated: 2026-04-11
---

# detect_follow_up

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 1072
**Signature:** `detect_follow_up(summary) → Optional[dict]`

Deterministic follow-up detector. If there's at least one unresolved
commitment, return a bounded intervention candidate dict. Prefer stale ones.
Returns None otherwise (caller falls back to existing decision/ambiguity logic).

Temporal v1: gated by FOLLOW_UP_COOLDOWN_SECONDS — suppresses repeat prompts
...

## Calls

- [[eos_ai-substrate-meeting_intelligence-py-_MeetingSummaryStore-get]]
- [[eos_ai-substrate-meeting_intelligence-py-_log]]
- [[eos_ai-substrate-meeting_intelligence-py-is_followup_in_cooldown]]
- [[eos_ai-substrate-meeting_intelligence-py-ownership_pressure_hint]]
- [[eos_ai-substrate-meeting_intelligence-py-unresolved_commitments]]

## Called By

- [[eos_ai-substrate-meeting_intelligence-py-detect_intervention]]
- [[eos_ai-substrate-meeting_intelligence-py-intelligence_report_block]]
