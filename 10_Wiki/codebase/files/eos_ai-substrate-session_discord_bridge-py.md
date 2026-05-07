---
type: codebase-file
path: eos_ai/substrate/session_discord_bridge.py
module: eos_ai.substrate.session_discord_bridge
lines: 459
size: 16256
generated: 2026-05-07
---

# eos_ai/substrate/session_discord_bridge.py

Session Discord Bridge — routes SessionWatcher events to Discord and back.

Receives state events from SessionWatcher, formats Discord notifications with
interactive buttons, and routes Discord responses back into tmux sessions.

...

**Lines:** 459 | **Size:** 16,256 bytes

## Depends On

- [[eos_ai-substrate-session_watcher-py]]

## Used By

- [[scripts-session_discord_control_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-session_discord_bridge-py-PlanApprovalView]] — 5 methods
- **class** [[eos_ai-substrate-session_discord_bridge-py-PermissionView]] — 4 methods
- **class** [[eos_ai-substrate-session_discord_bridge-py-QuestionOptionView]] — 3 methods
- **class** [[eos_ai-substrate-session_discord_bridge-py-SessionDiscordBridge]] — 6 methods
- **fn** [[eos_ai-substrate-session_discord_bridge-py-_extract_options]]`(text) → list[tuple[str, str]]`
- **fn** [[eos_ai-substrate-session_discord_bridge-py-format_event]]`(event) → dict[str, Any]`
- **fn** [[eos_ai-substrate-session_discord_bridge-py-_resolve_channel_id]]`(session_name) → int | None`
- **fn** [[eos_ai-substrate-session_discord_bridge-py-get_bridge]]`() → SessionDiscordBridge`
- **fn** [[eos_ai-substrate-session_discord_bridge-py-send_reply]]`(channel, text) → None`

## Import Statements

```python
from __future__ import annotations
import asyncio
import os
import re
import sys
import threading
from typing import Any
import discord
from eos_ai.substrate.session_watcher import SessionState
from eos_ai.substrate.session_watcher import WatcherEvent
from eos_ai.substrate.session_watcher import get_watcher
```
