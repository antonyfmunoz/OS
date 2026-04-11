---
type: codebase-file
path: scripts/workers/discord_approval_worker.py
module: scripts.workers.discord_approval_worker
lines: 234
size: 7493
tags: [entry-point]
generated: 2026-04-11
---

# scripts/workers/discord_approval_worker.py

> **ENTRY POINT** — Contains `if __name__` or server start.

discord_approval_worker.py — tail notifications.jsonl, post to Discord.

The Control Plane's `FileNotifier` writes every deferred-action
announcement to an append-only JSONL queue at
`/opt/OS/logs/deferred/notifications.jsonl`. This worker is the
...

**Lines:** 234 | **Size:** 7,493 bytes

## Contains

- **fn** [[scripts-workers-discord_approval_worker-py-_read_offset]]`() → int`
- **fn** [[scripts-workers-discord_approval_worker-py-_write_offset]]`(offset) → None`
- **fn** [[scripts-workers-discord_approval_worker-py-_is_still_deferred]]`(action_id) → bool`
- **fn** [[scripts-workers-discord_approval_worker-py-_format_discord_payload]]`(record) → dict`
- **fn** [[scripts-workers-discord_approval_worker-py-_post_to_discord]]`(webhook_url, payload, timeout) → tuple[bool, str]`
- **fn** [[scripts-workers-discord_approval_worker-py-_log]]`(msg) → None`
- **fn** [[scripts-workers-discord_approval_worker-py-drain_once]]`(webhook_url) → dict`
- **fn** [[scripts-workers-discord_approval_worker-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime
from datetime import timezone
```
