---
type: codebase-file
path: services/handlers/intent_handler.py
module: services.handlers.intent_handler
lines: 331
size: 11141
generated: 2026-04-12
---

# services/handlers/intent_handler.py

Intent classification and gateway routing.
Extracted from discord_bot.py — handles message intent
detection, request building, and gateway execution.

**Lines:** 331 | **Size:** 11,141 bytes

## Contains

- **fn** [[services-handlers-intent_handler-py-build_request]]`(text, intent, channel_name, username, default_venture_id) → dict`
- **fn** [[services-handlers-intent_handler-py-run_gateway]]`(text, channel_name, username, gateway, ki, channel_sessions, default_venture_id, guild_id, channel_id) → str`

## Import Statements

```python
import json
import os
import re
import sys
import uuid as _uuid_mod
from datetime import datetime
from zoneinfo import ZoneInfo
```
