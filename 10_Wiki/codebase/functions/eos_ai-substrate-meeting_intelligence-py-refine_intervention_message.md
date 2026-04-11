---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 1238
generated: 2026-04-11
---

# refine_intervention_message

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 1238
**Signature:** `refine_intervention_message(raw_message, role_slug, summary) → str`

Bounded, fallback-safe refinement of an intervention message.

Contract:
  - Trigger logic is NOT moved here; caller already decided to intervene.
  - If role is unknown → return raw_message untouched (capped).
...

## Calls

- [[eos_ai-substrate-meeting_intelligence-py-_MeetingSummaryStore-get]]
- [[eos_ai-substrate-meeting_intelligence-py-_log]]
- [[eos_ai-substrate-meeting_intelligence-py-_normalize_role]]

## Called By

- [[eos_ai-substrate-meeting_intelligence-py-maybe_emit_intervention]]
