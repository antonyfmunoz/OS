---
type: codebase-file
path: eos_ai/week_architect.py
module: eos_ai.week_architect
lines: 95
size: 3176
generated: 2026-04-11
---

# eos_ai/week_architect.py

WeekArchitect — designs the upcoming week using the Perfect Week
template as baseline, overlaid with real calendar events.

**Lines:** 95 | **Size:** 3,176 bytes

## Contains

- **fn** [[eos_ai-week_architect-py-architect_week]]`(ctx) → str`
- **fn** [[eos_ai-week_architect-py-_fallback_week]]`(ideal_week) → str`

## Import Statements

```python
import logging
import os
from datetime import datetime
from pathlib import Path as _Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
