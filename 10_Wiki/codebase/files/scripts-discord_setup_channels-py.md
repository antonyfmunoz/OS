---
type: codebase-file
path: scripts/discord_setup_channels.py
module: scripts.discord_setup_channels
lines: 195
size: 6249
tags: [entry-point]
generated: 2026-04-12
---

# scripts/discord_setup_channels.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Discord Builder/Product Channels Setup v1.

Idempotent operator automation:
  1. Log in as the EOS Discord bot.
  2. Locate the target guild (env override → single-guild auto-detect).
...

**Lines:** 195 | **Size:** 6,249 bytes

## Contains

- **fn** [[scripts-discord_setup_channels-py-_log]]`(msg) → None`
- **fn** [[scripts-discord_setup_channels-py-_load_token]]`() → str`
- **fn** [[scripts-discord_setup_channels-py-_run]]`() → dict`
- **fn** [[scripts-discord_setup_channels-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import asyncio
import json
import os
import sys
from pathlib import Path
```
