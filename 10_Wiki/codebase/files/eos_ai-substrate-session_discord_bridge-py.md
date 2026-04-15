---
type: codebase-file
path: eos_ai/substrate/session_discord_bridge.py
module: eos_ai.substrate.session_discord_bridge
lines: 288
size: 10131
generated: 2026-04-12
---

# eos_ai/substrate/session_discord_bridge.py

Session Discord Bridge — routes SessionWatcher events to Discord and back.

Receives state events from SessionWatcher, formats Discord notifications with
interactive buttons, and routes Discord responses back into tmux sessions.

...

**Lines:** 288 | **Size:** 10,131 bytes

## Depends On

- [[eos_ai-substrate-session_watcher-py]]

## Contains

- **class** [[eos_ai-substrate-session_discord_bridge-py-PlanApprovalView]] — 3 methods
- **class** [[eos_ai-substrate-session_discord_bridge-py-PermissionView]] — 3 methods
- **class** [[eos_ai-substrate-session_discord_bridge-py-SessionDiscordBridge]] — 5 methods
- **fn** [[eos_ai-substrate-session_discord_bridge-py-format_event]]`(event) → dict[str, Any]`
- **fn** [[eos_ai-substrate-session_discord_bridge-py-get_bridge]]`() → SessionDiscordBridge`

## Import Statements

```python
from __future__ import annotations
import asyncio
import os
import sys
import threading
from typing import Any
import discord
from eos_ai.substrate.session_watcher import SessionState
from eos_ai.substrate.session_watcher import WatcherEvent
from eos_ai.substrate.session_watcher import get_watcher
```
