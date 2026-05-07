---
type: codebase-file
path: services/local_bridge_client.py
module: services.local_bridge_client
lines: 134
size: 4252
generated: 2026-05-07
---

# services/local_bridge_client.py

Local Bridge Client — forwards Discord messages to Antony's local machine.

When Antony is at his PC (Windows/WSL via Tailscale), Discord messages route
to a Claude Code session running locally instead of the VPS tmux sessions.

...

**Lines:** 134 | **Size:** 4,252 bytes

## Contains

- **fn** [[services-local_bridge_client-py-is_bridge_enabled]]`() → bool`
- **fn** [[services-local_bridge_client-py-check_health]]`() → bool`
- **fn** [[services-local_bridge_client-py-forward_to_local]]`(text, session_name) → bool`
- **fn** [[services-local_bridge_client-py-bridge_status]]`() → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import logging
import os
import sys
from pathlib import Path
from typing import Any
import requests
from dotenv import load_dotenv
```
