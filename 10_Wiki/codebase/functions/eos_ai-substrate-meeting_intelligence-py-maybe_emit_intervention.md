---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 1298
generated: 2026-04-12
---

# maybe_emit_intervention

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 1298
**Signature:** `maybe_emit_intervention(node_id, meeting_id, summary) → Optional[dict]`

Detect + emit SPEAK_TEXT intervention. Never raises.

## Calls

- [[eos_ai-substrate-meeting_intelligence-py-_MeetingSummaryStore-get]]
- [[eos_ai-substrate-meeting_intelligence-py-_MeetingSummaryStore-put]]
- [[eos_ai-substrate-meeting_intelligence-py-_MeetingSummaryStore-record_intervention]]
- [[eos_ai-substrate-meeting_intelligence-py-_log]]
- [[eos_ai-substrate-meeting_intelligence-py-derive_active_role]]
- [[eos_ai-substrate-meeting_intelligence-py-detect_intervention]]
- [[eos_ai-substrate-meeting_intelligence-py-get_meeting_summary_store]]
- [[eos_ai-substrate-meeting_intelligence-py-refine_intervention_message]]

## Called By

- [[eos_ai-substrate-meeting_intelligence-py-on_utterance_injected]]
