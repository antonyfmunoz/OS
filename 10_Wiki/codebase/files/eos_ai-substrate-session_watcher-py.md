---
type: codebase-file
path: eos_ai/substrate/session_watcher.py
module: eos_ai.substrate.session_watcher
lines: 747
size: 27954
generated: 2026-05-07
---

# eos_ai/substrate/session_watcher.py

Session Watcher — continuous tmux state machine for Claude Code sessions.

Replaces blind before/after polling in ask_session with state-aware monitoring.
One SessionWatcher instance per tmux session (dex_builder_main, dex_product_main).
Runs as a daemon thread, polls tmux pane every 0.5s, detects session state,
...

**Lines:** 747 | **Size:** 27,954 bytes

## Depends On

- [[eos_ai-substrate-claude_session_bridge-py]]

## Used By

- [[eos_ai-substrate-session_discord_bridge-py]]
- [[scripts-direct_watcher_path_smoke_test-py]]
- [[scripts-session_discord_control_smoke_test-py]]
- [[scripts-session_watcher_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-session_watcher-py-SessionState]] — 0 methods
- **class** [[eos_ai-substrate-session_watcher-py-WatcherEvent]] — 1 methods
- **class** [[eos_ai-substrate-session_watcher-py-SessionWatcher]] — 16 methods
- **fn** [[eos_ai-substrate-session_watcher-py-get_watcher]]`(session_name) → SessionWatcher | None`
- **fn** [[eos_ai-substrate-session_watcher-py-start_watcher]]`(target, session_name) → SessionWatcher`
- **fn** [[eos_ai-substrate-session_watcher-py-stop_watcher]]`(session_name) → None`
- **fn** [[eos_ai-substrate-session_watcher-py-stop_all_watchers]]`() → None`
- **fn** [[eos_ai-substrate-session_watcher-py-ask_session_watched]]`(target, session_name, text) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import enum
import re
import threading
import time
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Callable
from eos_ai.substrate.claude_session_bridge import capture_output
from eos_ai.substrate.claude_session_bridge import send_message
```
