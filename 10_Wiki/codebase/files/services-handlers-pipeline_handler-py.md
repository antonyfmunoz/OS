---
type: codebase-file
path: services/handlers/pipeline_handler.py
module: services.handlers.pipeline_handler
lines: 139
size: 3585
generated: 2026-04-12
---

# services/handlers/pipeline_handler.py

Pipeline update detection and Notion stage updates.
Extracted from discord_bot.py — detects natural language
pipeline signals (won/lost/booked) and updates Notion.

**Lines:** 139 | **Size:** 3,585 bytes

## Contains

- **fn** [[services-handlers-pipeline_handler-py-detect_pipeline_update]]`(text) → tuple[str, str] | None`
- **fn** [[services-handlers-pipeline_handler-py-handle_pipeline_update]]`(message, text) → bool`

## Import Statements

```python
import re
import sys
import os
```
