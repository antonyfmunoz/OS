---
type: codebase-file
path: eos_ai/ideal_week.py
module: eos_ai.ideal_week
lines: 264
size: 8728
generated: 2026-04-12
---

# eos_ai/ideal_week.py

Ideal Week — stores and applies Antony's ideal
week template. Used by week_architect.py as baseline.

**Lines:** 264 | **Size:** 8,728 bytes

## Contains

- **fn** [[eos_ai-ideal_week-py-get_ideal_week]]`(ctx) → dict`
- **fn** [[eos_ai-ideal_week-py-save_ideal_week]]`(template, ctx) → bool`
- **fn** [[eos_ai-ideal_week-py-create_process_capture]]`(task_name, description, ctx) → str`
- **fn** [[eos_ai-ideal_week-py-save_annual_architecture]]`(year_plan, ctx) → bool`
- **fn** [[eos_ai-ideal_week-py-get_annual_architecture]]`(ctx) → dict`
- **fn** [[eos_ai-ideal_week-py-get_current_quarter_rocks]]`(ctx) → list[str]`

## Import Statements

```python
import json
import logging
import re
from datetime import datetime
from pathlib import Path as _Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
