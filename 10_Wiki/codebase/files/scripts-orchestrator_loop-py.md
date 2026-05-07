---
type: codebase-file
path: scripts/orchestrator_loop.py
module: scripts.orchestrator_loop
lines: 74
size: 2228
tags: [entry-point]
generated: 2026-05-07
---

# scripts/orchestrator_loop.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Orchestrator loop runner.

Usage:
    python3 scripts/orchestrator_loop.py              # one cycle, print JSON report
    python3 scripts/orchestrator_loop.py --cycles 3   # run N cycles with sleep
...

**Lines:** 74 | **Size:** 2,228 bytes

## Depends On

- [[core-orchestrator-loop-py]]
- [[core-orchestrator-orchestrator-py]]
- [[core-orchestrator-workflows-py]]

## Contains

- **fn** [[scripts-orchestrator_loop-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from core.orchestrator.loop import LoopConfig
from core.orchestrator.loop import run_cycle
from core.orchestrator.loop import run_forever
from core.orchestrator.orchestrator import default_orchestrator
from core.orchestrator.workflows import register_default_workflows
```
