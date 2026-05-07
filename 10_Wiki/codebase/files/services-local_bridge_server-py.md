---
type: codebase-file
path: services/local_bridge_server.py
module: services.local_bridge_server
lines: 243
size: 8266
tags: [entry-point]
generated: 2026-05-07
---

# services/local_bridge_server.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Local Bridge Server — runs on Antony's Windows machine (WSL2).

Receives Discord messages forwarded from the VPS and injects them into
a local Claude Code tmux session.

...

**Lines:** 243 | **Size:** 8,266 bytes

## Contains

- **fn** [[services-local_bridge_server-py-_tmux_has_session]]`(session_name) → bool`
- **fn** [[services-local_bridge_server-py-_tmux_send]]`(session_name, text) → bool`
- **fn** [[services-local_bridge_server-py-_inject_message]]`(session_name, text) → dict`
- **fn** [[services-local_bridge_server-py-handle_health]]`(_request) → web.Response`
- **fn** [[services-local_bridge_server-py-handle_message]]`(request) → web.Response`
- **fn** [[services-local_bridge_server-py-handle_status]]`(_request) → web.Response`
- **fn** [[services-local_bridge_server-py-create_app]]`() → web.Application`

## Import Statements

```python
from __future__ import annotations
import asyncio
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from aiohttp import web
```
