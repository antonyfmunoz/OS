---
type: codebase-file
path: scripts/call_prep.py
module: scripts.call_prep
lines: 431
size: 15807
tags: [entry-point]
generated: 2026-04-11
---

# scripts/call_prep.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Call Prep — runs every 15 minutes via cron.
Checks GWS calendar for events starting in the next 25-45 minutes.
Fires a proactive prep brief to Discord if one is found.

**Lines:** 431 | **Size:** 15,807 bytes

## Contains

- **fn** [[scripts-call_prep-py-get_upcoming_calls]]`(window_start_mins, window_end_mins) → list`
- **fn** [[scripts-call_prep-py-build_prep_brief]]`(event, ctx) → str`
- **fn** [[scripts-call_prep-py-post_to_discord]]`(message) → bool`
- **fn** [[scripts-call_prep-py-already_prepped]]`(event_id) → bool`
- **fn** [[scripts-call_prep-py-mark_prepped]]`(event_id) → None`
- **fn** [[scripts-call_prep-py-main]]`()`

## Import Statements

```python
import sys
import os
from datetime import datetime
from datetime import timezone
from datetime import timedelta
from dotenv import load_dotenv
```
