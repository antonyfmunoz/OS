---
type: codebase-file
path: scripts/router_claude_runtime_debug.py
module: scripts.router_claude_runtime_debug
lines: 75
size: 2845
tags: [entry-point]
generated: 2026-05-07
---

# scripts/router_claude_runtime_debug.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Router runtime debug helper — prints the actual, live state the router
sees for the Claude CLI backend.

Run inside the target environment (host OR `docker exec os-discord python3
scripts/router_claude_runtime_debug.py`) to prove:
...

**Lines:** 75 | **Size:** 2,845 bytes

## Contains

- **fn** [[scripts-router_claude_runtime_debug-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import json
import os
import sys
```
