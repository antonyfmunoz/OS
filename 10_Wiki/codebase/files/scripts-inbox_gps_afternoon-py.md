---
type: codebase-file
path: scripts/inbox_gps_afternoon.py
module: scripts.inbox_gps_afternoon
lines: 30
size: 824
generated: 2026-05-07
---

# scripts/inbox_gps_afternoon.py

Email GPS — 3pm afternoon inbox pass.
Runs via cron at 15:00 daily.
Posts report to Discord if there's anything to surface.

**Lines:** 30 | **Size:** 824 bytes

## Depends On

- [[eos_ai-context-py]]
- [[eos_ai-discord_utils-py]]
- [[eos_ai-email_gps-py]]

## Import Statements

```python
import sys
import os
from dotenv import load_dotenv
from eos_ai.email_gps import EmailGPS
from eos_ai.context import load_context_from_env
from eos_ai.discord_utils import post_to_webhook
```
