---
type: codebase-file
path: scripts/permission_notify.py
module: scripts.permission_notify
lines: 103
size: 2466
tags: [entry-point]
generated: 2026-05-07
---

# scripts/permission_notify.py

> **ENTRY POINT** — Contains `if __name__` or server start.

PermissionRequest hook.
Channel-agnostic permission notification.
Uses ChannelRouter — works with Discord,
Telegram, Webhook, or any configured channel.

**Lines:** 103 | **Size:** 2,466 bytes

## Contains

- **fn** [[scripts-permission_notify-py-is_safe]]`(tool_name, tool_input) → bool`
- **fn** [[scripts-permission_notify-py-log_permission]]`(tool_name, tool_use_id, safe) → None`
- **fn** [[scripts-permission_notify-py-main]]`()`

## Import Statements

```python
import sys
import os
import json
import time
```
