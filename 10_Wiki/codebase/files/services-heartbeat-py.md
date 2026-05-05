---
type: codebase-file
path: services/heartbeat.py
module: services.heartbeat
lines: 113
size: 2985
tags: [entry-point]
generated: 2026-04-12
---

# services/heartbeat.py

> **ENTRY POINT** — Contains `if __name__` or server start.

EOS Heartbeat Service
=====================
Scheduled jobs that run independent of Claude Code.
System health monitoring, self-awareness checks,
and periodic maintenance.
...

**Lines:** 113 | **Size:** 2,985 bytes

## Contains

- **fn** [[services-heartbeat-py-system_health_heartbeat]]`() → None`
- **fn** [[services-heartbeat-py-run_once]]`() → None`
- **fn** [[services-heartbeat-py-run_loop]]`() → None`

## Import Statements

```python
import json
import logging
import os
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
