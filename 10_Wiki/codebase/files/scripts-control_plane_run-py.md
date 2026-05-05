---
type: codebase-file
path: scripts/control_plane_run.py
module: scripts.control_plane_run
lines: 105
size: 3401
tags: [entry-point]
generated: 2026-04-12
---

# scripts/control_plane_run.py

> **ENTRY POINT** — Contains `if __name__` or server start.

control_plane_run.py — run a shell command or script through the Control Plane.

This is the reference integration for orchestration hooks. Instead of
calling subprocess directly, agents (and humans) should route meaningful
work through this entry point so every execution is validated, approved,
...

**Lines:** 105 | **Size:** 3,401 bytes

## Depends On

- [[core-action_system-control_plane-py]]

## Contains

- **fn** [[scripts-control_plane_run-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from core.action_system.control_plane import run_action
from core.action_system.control_plane import log_decision
```
