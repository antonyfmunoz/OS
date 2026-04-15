---
type: codebase-file
path: scripts/eos_os.py
module: scripts.eos_os
lines: 398
size: 12333
tags: [entry-point]
generated: 2026-04-12
---

# scripts/eos_os.py

> **ENTRY POINT** — Contains `if __name__` or server start.

eos_os.py — Unified operator CLI for the EOS AI Operating System.

This is the single surface an operator uses to drive the system. Every
command in here maps 1:1 to something in the architecture doc
(core/ARCHITECTURE_FINAL.md).
...

**Lines:** 398 | **Size:** 12,333 bytes

## Depends On

- [[core-observability-py]]

## Contains

- **fn** [[scripts-eos_os-py-_dumps]]`(obj) → str`
- **fn** [[scripts-eos_os-py-_header]]`(text) → str`
- **fn** [[scripts-eos_os-py-_cmd_status]]`(args) → int`
- **fn** [[scripts-eos_os-py-_cmd_agents]]`(args) → int`
- **fn** [[scripts-eos_os-py-_cmd_workflows]]`(args) → int`
- **fn** [[scripts-eos_os-py-_cmd_actions]]`(args) → int`
- **fn** [[scripts-eos_os-py-_cmd_harness]]`(args) → int`
- **fn** [[scripts-eos_os-py-_cmd_failures]]`(args) → int`
- **fn** [[scripts-eos_os-py-_cmd_optimizer]]`(args) → int`
- **fn** [[scripts-eos_os-py-_cmd_workflow_run]]`(args) → int`
- **fn** [[scripts-eos_os-py-_cmd_tick_agents]]`(args) → int`
- **fn** [[scripts-eos_os-py-_cmd_start]]`(args) → int`
- **fn** [[scripts-eos_os-py-_cmd_verify]]`(args) → int`
- **fn** [[scripts-eos_os-py-_cmd_sandbox]]`(args) → int`
- **fn** [[scripts-eos_os-py-_cmd_sandboxes]]`(args) → int`
- **fn** [[scripts-eos_os-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any
from core.observability import Observability
```
