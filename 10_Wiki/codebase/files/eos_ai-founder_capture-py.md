---
type: codebase-file
path: eos_ai/founder_capture.py
module: eos_ai.founder_capture
lines: 227
size: 7679
generated: 2026-04-12
---

# eos_ai/founder_capture.py

Founder Capture — detects tasks, ideas, and reminders from Discord messages
and writes them to the Neon events table so they appear in the morning brief
Section 1 (Your list). Also pushes to Notion dashboard.

**Lines:** 227 | **Size:** 7,679 bytes

## Contains

- **fn** [[eos_ai-founder_capture-py-should_capture]]`(text) → tuple[bool, str]`
- **fn** [[eos_ai-founder_capture-py-_classify_venture]]`(text) → str`
- **fn** [[eos_ai-founder_capture-py-capture_to_neon]]`(text, capture_type, ctx) → bool`
- **fn** [[eos_ai-founder_capture-py-capture_to_notion]]`(text, capture_type, venture_id) → bool`
- **fn** [[eos_ai-founder_capture-py-capture]]`(text, ctx, venture_id) → dict`

## Import Statements

```python
import json
import logging
from datetime import datetime
from datetime import timezone
```
