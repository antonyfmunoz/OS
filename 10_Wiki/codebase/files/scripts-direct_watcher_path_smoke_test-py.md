---
type: codebase-file
path: scripts/direct_watcher_path_smoke_test.py
module: scripts.direct_watcher_path_smoke_test
lines: 262
size: 9208
generated: 2026-05-07
---

# scripts/direct_watcher_path_smoke_test.py

Smoke test — Direct CC Watcher Path for Discord messages.

Validates that the direct watcher path in discord_bot.on_message:
  1. Resolves the correct session name from Discord mode routing
  2. Detects active watchers
...

**Lines:** 262 | **Size:** 9,208 bytes

## Depends On

- [[eos_ai-substrate-claude_session_bridge-py]]
- [[eos_ai-substrate-discord_mode_routing-py]]
- [[eos_ai-substrate-session_watcher-py]]

## Contains

- **fn** [[scripts-direct_watcher_path_smoke_test-py-check]]`(name, condition, detail) → None`

## Import Statements

```python
import os
import sys
import threading
import time
from eos_ai.substrate.discord_mode_routing import resolve_discord_mode
from eos_ai.substrate.discord_mode_routing import resolve_mode_session
from eos_ai.substrate.session_watcher import get_watcher
from eos_ai.substrate.session_watcher import start_watcher
from eos_ai.substrate.session_watcher import ask_session_watched
from eos_ai.substrate.claude_session_bridge import _scrub_cli_chrome
```
