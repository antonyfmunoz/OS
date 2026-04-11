---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 1395
generated: 2026-04-11
---

# on_utterance_injected

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 1395
**Signature:** `on_utterance_injected(node_id, meeting_id, recent_utterances) → None`

Wrapper the transport calls after each inject_utterance. Never raises.

## Calls

- [[eos_ai-substrate-meeting_intelligence-py-_MeetingSummaryStore-get]]
- [[eos_ai-substrate-meeting_intelligence-py-_log]]
- [[eos_ai-substrate-meeting_intelligence-py-extract_memory]]
- [[eos_ai-substrate-meeting_intelligence-py-get_meeting_summary_store]]
- [[eos_ai-substrate-meeting_intelligence-py-maybe_emit_intervention]]
- [[eos_ai-substrate-meeting_intelligence-py-update_meeting_summary]]
