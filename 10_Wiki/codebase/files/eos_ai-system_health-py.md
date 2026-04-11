---
type: codebase-file
path: eos_ai/system_health.py
module: eos_ai.system_health
lines: 436
size: 13972
tags: [entry-point]
generated: 2026-04-11
---

# eos_ai/system_health.py

> **ENTRY POINT** — Contains `if __name__` or server start.

EOS System Health Monitor
=========================
EOS monitors its own operational state.
Runs at: SessionStart, heartbeat every 30min,
after every gateway call.
...

**Lines:** 436 | **Size:** 13,972 bytes

## Contains

- **class** [[eos_ai-system_health-py-EOSSystemHealth]] — 9 methods
- **fn** [[eos_ai-system_health-py-get_system_health]]`(ctx) → EOSSystemHealth`

## Import Statements

```python
import json
import logging
import os
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo
```
