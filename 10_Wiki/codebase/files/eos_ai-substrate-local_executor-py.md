---
type: codebase-file
path: eos_ai/substrate/local_executor.py
module: eos_ai.substrate.local_executor
lines: 216
size: 7715
generated: 2026-05-07
---

# eos_ai/substrate/local_executor.py

Control Layer v1 — Local Agent (Executor).

Polls the control_bridge queue for a node and runs whitelisted actions
inside a strict sandbox. NEVER raises. ALWAYS returns a result dict.

...

**Lines:** 216 | **Size:** 7,715 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]

## Contains

- **fn** [[eos_ai-substrate-local_executor-py-_ensure_sandbox]]`() → None`
- **fn** [[eos_ai-substrate-local_executor-py-_truncate]]`(s) → str`
- **fn** [[eos_ai-substrate-local_executor-py-_result]]`(cmd, ok) → dict[str, Any]`
- **fn** [[eos_ai-substrate-local_executor-py-_do_run_shell]]`(cmd) → dict[str, Any]`
- **fn** [[eos_ai-substrate-local_executor-py-_do_write_file]]`(cmd) → dict[str, Any]`
- **fn** [[eos_ai-substrate-local_executor-py-_do_run_python]]`(cmd) → dict[str, Any]`
- **fn** [[eos_ai-substrate-local_executor-py-execute_command]]`(cmd) → dict[str, Any]`
- **fn** [[eos_ai-substrate-local_executor-py-process_pending]]`(node_id) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import os
import subprocess
import time
from pathlib import Path
from typing import Any
from eos_ai.substrate import control_bridge as bridge
from eos_ai.substrate import control_commands as cc
```
