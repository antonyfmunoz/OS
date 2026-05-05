---
type: codebase-file
path: eos_ai/document_filer.py
module: eos_ai.document_filer
lines: 143
size: 4163
generated: 2026-04-12
---

# eos_ai/document_filer.py

Document Filing System — intelligently files documents
arriving via email to the correct Drive folder.
Uses LLM to classify then logs to Neon.

**Lines:** 143 | **Size:** 4,163 bytes

## Contains

- **fn** [[eos_ai-document_filer-py-classify_document]]`(filename, subject, sender) → dict`
- **fn** [[eos_ai-document_filer-py-log_document]]`(filename, doc_type, folder, venture, sender, requires_review, ctx) → bool`
- **fn** [[eos_ai-document_filer-py-process_email_attachments]]`(subject, sender, attachment_names, ctx) → list[dict]`

## Import Statements

```python
import os
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
