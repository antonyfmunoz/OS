---
type: codebase-file
path: core/action_system/notifier.py
module: core.action_system.notifier
lines: 120
size: 4304
generated: 2026-04-12
---

# core/action_system/notifier.py

Notifier foundation for deferred actions.

Two implementations ship in v2:

- FileNotifier  — always-on, writes an append-only JSONL queue that
...

**Lines:** 120 | **Size:** 4,304 bytes

## Used By

- [[core-orchestrator-handlers-py]]

## Contains

- **class** [[core-action_system-notifier-py-Notifier]] — 1 methods
- **class** [[core-action_system-notifier-py-FileNotifier]] — 2 methods
- **class** [[core-action_system-notifier-py-DiscordNotifier]] — 2 methods
- **class** [[core-action_system-notifier-py-MultiNotifier]] — 2 methods
- **fn** [[core-action_system-notifier-py-default_notifier]]`() → Notifier`

## Import Statements

```python
from __future__ import annotations
import json
import os
from datetime import datetime
from datetime import timezone
from typing import Protocol
from actions import Action
```
