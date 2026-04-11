---
type: codebase-file
path: eos_ai/gws_connector.py
module: eos_ai.gws_connector
lines: 1035
size: 36063
generated: 2026-04-11
---

# eos_ai/gws_connector.py

GWSConnector — Google Workspace integration via gws CLI.

Provides calendar, tasks, drive, and gmail access for EOS agents.
All methods are safe — they log warnings on error and never crash.

...

**Lines:** 1035 | **Size:** 36,063 bytes

## Used By

- [[eos_ai-onboarding_backfill-py]]
- [[scripts-inbox_zero_init-py]]

## Contains

- **class** [[eos_ai-gws_connector-py-GWSConnector]] — 35 methods
- **fn** [[eos_ai-gws_connector-py-_in_cooldown]]`() → float`
- **fn** [[eos_ai-gws_connector-py-_trip_cooldown]]`() → None`

## Import Statements

```python
import json
import os
import subprocess
import time
from datetime import datetime
from datetime import timezone
from datetime import timedelta
from pathlib import Path as _Path
from dotenv import load_dotenv as _load_dotenv
```
