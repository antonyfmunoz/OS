---
type: codebase-file
path: scripts/eos_status.py
module: scripts.eos_status
lines: 161
size: 5077
tags: [entry-point]
generated: 2026-04-11
---

# scripts/eos_status.py

> **ENTRY POINT** — Contains `if __name__` or server start.

EOS Operator Status — single inspectable surface.

Shows everything an operator needs to trust the substrate at a glance:
- provider health (with reasons)
- Docker service status
...

**Lines:** 161 | **Size:** 5,077 bytes

## Depends On

- [[eos_ai-provider_health-py]]

## Contains

- **fn** [[scripts-eos_status-py-section]]`(title) → None`
- **fn** [[scripts-eos_status-py-docker_status]]`() → str`
- **fn** [[scripts-eos_status-py-cron_recent_runs]]`() → str`
- **fn** [[scripts-eos_status-py-active_locks]]`() → str`
- **fn** [[scripts-eos_status-py-recent_provider_errors]]`() → str`
- **fn** [[scripts-eos_status-py-main]]`() → int`

## Import Statements

```python
import os
import sys
import subprocess
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv
from eos_ai.provider_health import check_all
```
