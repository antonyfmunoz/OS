---
type: codebase-file
path: eos_ai/confidentiality.py
module: eos_ai.confidentiality
lines: 119
size: 3459
generated: 2026-04-11
---

# eos_ai/confidentiality.py

Confidentiality Protocol — handles sensitive
negotiations, investor terms, M&A discussions,
and any context requiring restricted logging.

**Lines:** 119 | **Size:** 3,459 bytes

## Contains

- **fn** [[eos_ai-confidentiality-py-detect_confidential_context]]`(text) → dict`
- **fn** [[eos_ai-confidentiality-py-create_confidential_session]]`(topic, parties, level, ctx) → dict`

## Import Statements

```python
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
