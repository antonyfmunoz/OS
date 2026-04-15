---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 470
generated: 2026-04-12
---

# update_meeting_summary

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 470
**Signature:** `update_meeting_summary(node_id, meeting_id, utterances) → dict[str, Any]`

Update (or create) the rolling meeting summary. Never raises.

## Calls

- [[eos_ai-substrate-meeting_intelligence-py-ActionableItem-as_dict]]
- [[eos_ai-substrate-meeting_intelligence-py-Commitment-as_dict]]
- [[eos_ai-substrate-meeting_intelligence-py-ExtractedMemory-as_dict]]
- [[eos_ai-substrate-meeting_intelligence-py-MeetingSummary-as_dict]]
- [[eos_ai-substrate-meeting_intelligence-py-_MeetingSummaryStore-get]]
- [[eos_ai-substrate-meeting_intelligence-py-_MeetingSummaryStore-put]]
- [[eos_ai-substrate-meeting_intelligence-py-_apply_pressure_decay]]
- [[eos_ai-substrate-meeting_intelligence-py-_build_prompt]]
- [[eos_ai-substrate-meeting_intelligence-py-_cap_list]]
- [[eos_ai-substrate-meeting_intelligence-py-_extract_json_block]]
- [[eos_ai-substrate-meeting_intelligence-py-_fallback_summary]]
- [[eos_ai-substrate-meeting_intelligence-py-_log]]
- [[eos_ai-substrate-meeting_intelligence-py-_merge_commitments]]
- [[eos_ai-substrate-meeting_intelligence-py-_update_escalation_trend]]
- [[eos_ai-substrate-meeting_intelligence-py-compute_escalation_level]]
- [[eos_ai-substrate-meeting_intelligence-py-compute_scores]]
- [[eos_ai-substrate-meeting_intelligence-py-extract_commitments]]
- [[eos_ai-substrate-meeting_intelligence-py-get_meeting_summary_store]]
- [[eos_ai-substrate-meeting_intelligence-py-resolve_commitments]]

## Called By

- [[eos_ai-substrate-meeting_intelligence-py-on_utterance_injected]]
