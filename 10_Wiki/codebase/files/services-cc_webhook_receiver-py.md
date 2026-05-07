---
type: codebase-file
path: services/cc_webhook_receiver.py
module: services.cc_webhook_receiver
lines: 240
size: 8649
generated: 2026-05-07
---

# services/cc_webhook_receiver.py

CC Reply Webhook Receiver — receives POSTs from the CC Stop hook and
dispatches replies to Discord channels.

Architecture:
    CC session completes a turn
...

**Lines:** 240 | **Size:** 8,649 bytes

## Contains

- **fn** [[services-cc_webhook_receiver-py-_build_session_channel_map]]`() → dict[str, int]`
- **fn** [[services-cc_webhook_receiver-py-_chunk_message]]`(content, max_len) → list[str]`
- **fn** [[services-cc_webhook_receiver-py-start_webhook_server]]`(bot, ai_name, port) → web.AppRunner`

## Import Statements

```python
from __future__ import annotations
import json
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING
from aiohttp import web
from dotenv import load_dotenv
```
