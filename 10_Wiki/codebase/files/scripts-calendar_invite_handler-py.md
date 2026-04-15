---
type: codebase-file
path: scripts/calendar_invite_handler.py
module: scripts.calendar_invite_handler
lines: 300
size: 11025
tags: [entry-point]
generated: 2026-04-12
---

# scripts/calendar_invite_handler.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Calendar Invite Handler — polls for pending invites every 15 mins.
DEX reviews each one, decides accept/decline based on rules,
notifies Antony in Discord, logs to Notion Meetings DB.

**Lines:** 300 | **Size:** 11,025 bytes

## Contains

- **fn** [[scripts-calendar_invite_handler-py-load_state]]`()`
- **fn** [[scripts-calendar_invite_handler-py-save_state]]`(state)`
- **fn** [[scripts-calendar_invite_handler-py-get_pending_invites]]`() → list[dict]`
- **fn** [[scripts-calendar_invite_handler-py-assess_invite]]`(invite) → dict`
- **fn** [[scripts-calendar_invite_handler-py-respond_to_invite]]`(event_id, response) → bool`
- **fn** [[scripts-calendar_invite_handler-py-process_invites]]`()`

## Import Statements

```python
import os
import sys
import json
import asyncio
import discord
from datetime import datetime
from datetime import timezone
from datetime import timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
```
