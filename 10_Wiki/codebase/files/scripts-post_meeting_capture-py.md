---
type: codebase-file
path: scripts/post_meeting_capture.py
module: scripts.post_meeting_capture
lines: 135
size: 3769
tags: [entry-point]
generated: 2026-04-12
---

# scripts/post_meeting_capture.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Post-meeting capture — polls for recently ended calendar events
and prompts DEX to capture outcomes in Discord.

Runs every 15 minutes via cron. Deduplicates via /tmp/post_meeting_state.json.

**Lines:** 135 | **Size:** 3,769 bytes

## Contains

- **fn** [[scripts-post_meeting_capture-py-load_state]]`() → dict`
- **fn** [[scripts-post_meeting_capture-py-save_state]]`(state) → None`
- **fn** [[scripts-post_meeting_capture-py-check_and_prompt]]`() → None`

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
