---
type: codebase-file
path: scripts/session_start_context.py
module: scripts.session_start_context
lines: 199
size: 5529
tags: [entry-point]
generated: 2026-04-12
---

# scripts/session_start_context.py

> **ENTRY POINT** — Contains `if __name__` or server start.

SessionStart hook.
Injects dynamic context into every CC session.
Boris: "Dynamically load context each time
you start Claude (SessionStart)"

...

**Lines:** 199 | **Size:** 5,529 bytes

## Contains

- **fn** [[scripts-session_start_context-py-_timeout_handler]]`(signum, frame)`
- **fn** [[scripts-session_start_context-py-_acquire_lock]]`()`
- **fn** [[scripts-session_start_context-py-get_cc_version]]`() → str`
- **fn** [[scripts-session_start_context-py-check_version_change]]`(current) → bool`
- **fn** [[scripts-session_start_context-py-get_pending_tasks]]`() → int`
- **fn** [[scripts-session_start_context-py-get_venture_stage]]`() → str`
- **fn** [[scripts-session_start_context-py-get_system_health_summary]]`() → str`
- **fn** [[scripts-session_start_context-py-main]]`()`

## Import Statements

```python
import sys
import os
import signal
import subprocess
import fcntl
from datetime import datetime
from zoneinfo import ZoneInfo
```
