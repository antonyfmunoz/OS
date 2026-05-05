---
type: codebase-function
file: eos_ai/substrate/meeting_intelligence.py
line: 1360
generated: 2026-04-12
---

# extract_memory

**File:** [[eos_ai-substrate-meeting_intelligence-py]] | **Line:** 1360
**Signature:** `extract_memory(summary) → list[ExtractedMemory]`

Turn summary fields into ExtractedMemory objects. Never raises.

## Calls

- [[eos_ai-substrate-meeting_intelligence-py-_MeetingSummaryStore-put_memories]]
- [[eos_ai-substrate-meeting_intelligence-py-_log]]
- [[eos_ai-substrate-meeting_intelligence-py-get_meeting_summary_store]]

## Called By

- [[eos_ai-substrate-meeting_intelligence-py-on_utterance_injected]]
