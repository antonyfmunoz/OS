---
type: codebase-file
path: scripts/emit_signal.py
module: scripts.emit_signal
lines: 68
size: 1873
tags: [entry-point]
generated: 2026-04-12
---

# scripts/emit_signal.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Emit an orchestrator signal from cron or the shell.

Usage:
    python3 scripts/emit_signal.py <signal_name>
    python3 scripts/emit_signal.py <signal_name> --payload-json '{"k":"v"}'
...

**Lines:** 68 | **Size:** 1,873 bytes

## Depends On

- [[core-orchestrator-signals-py]]

## Contains

- **fn** [[scripts-emit_signal-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from core.orchestrator.signals import emit_signal
```
