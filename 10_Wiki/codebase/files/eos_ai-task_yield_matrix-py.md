---
type: codebase-file
path: eos_ai/task_yield_matrix.py
module: eos_ai.task_yield_matrix
lines: 176
size: 6209
generated: 2026-04-12
---

# eos_ai/task_yield_matrix.py

Task Yield Matrix — Dan Martell's task audit framework.
Delegate, Replace, Invest, Produce.
Audits tasks by energy impact and financial value.

**Lines:** 176 | **Size:** 6,209 bytes

## Contains

- **fn** [[eos_ai-task_yield_matrix-py-classify_task_yield]]`(task, ctx) → dict`
- **fn** [[eos_ai-task_yield_matrix-py-run_yield_audit]]`(tasks, ctx) → dict`
- **fn** [[eos_ai-task_yield_matrix-py-format_yield_report]]`(results) → str`

## Import Statements

```python
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
