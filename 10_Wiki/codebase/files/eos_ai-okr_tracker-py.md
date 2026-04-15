---
type: codebase-file
path: eos_ai/okr_tracker.py
module: eos_ai.okr_tracker
lines: 119
size: 3919
generated: 2026-04-12
---

# eos_ai/okr_tracker.py

OKR Tracker — tracks Objectives and Key Results per venture.
Weekly check-in cadence. Stored in Neon events table.

**Lines:** 119 | **Size:** 3,919 bytes

## Contains

- **fn** [[eos_ai-okr_tracker-py-set_okr]]`(objective, key_results, venture_id, quarter, ctx) → bool`
- **fn** [[eos_ai-okr_tracker-py-get_okrs]]`(venture_id, ctx) → list`
- **fn** [[eos_ai-okr_tracker-py-generate_okr_report]]`(ctx) → str`

## Import Statements

```python
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from dotenv import load_dotenv
```
