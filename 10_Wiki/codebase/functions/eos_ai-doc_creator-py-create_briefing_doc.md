---
type: codebase-function
file: eos_ai/doc_creator.py
line: 18
generated: 2026-04-12
---

# create_briefing_doc

**File:** [[eos_ai-doc_creator-py]] | **Line:** 18
**Signature:** `create_briefing_doc(title, topic, context, audience, doc_type, ctx) → dict`

Generate a briefing document using LLM and save to Google Drive.
doc_type: briefing | board_update | investor_update | proposal
Returns dict with content, drive_file, title, type.
