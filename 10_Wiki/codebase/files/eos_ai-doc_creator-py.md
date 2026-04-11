---
type: codebase-file
path: eos_ai/doc_creator.py
module: eos_ai.doc_creator
lines: 371
size: 9576
generated: 2026-04-11
---

# eos_ai/doc_creator.py

Document Creator — generates briefing docs, board updates,
investor updates, proposals, and presentation outlines using
LLM + Google Drive.

**Lines:** 371 | **Size:** 9,576 bytes

## Contains

- **fn** [[eos_ai-doc_creator-py-create_briefing_doc]]`(title, topic, context, audience, doc_type, ctx) → dict`
- **fn** [[eos_ai-doc_creator-py-create_presentation_outline]]`(title, topic, slides, audience, ctx) → dict`
- **fn** [[eos_ai-doc_creator-py-fact_check]]`(claim, ctx) → dict`
- **fn** [[eos_ai-doc_creator-py-draft_announcement]]`(topic, audience, key_message, context, announcement_type, ctx) → str`
- **fn** [[eos_ai-doc_creator-py-draft_crisis_communication]]`(situation, affected_parties, what_happened, what_we_are_doing, ctx) → str`

## Import Statements

```python
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
