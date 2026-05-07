---
type: codebase-file
path: core/action_system/executor.py
module: core.action_system.executor
lines: 133
size: 4769
generated: 2026-05-07
---

# core/action_system/executor.py

Action executors — dispatch by action.type.

Each executor returns a JSON-serialisable dict. Failures are captured as
{"ok": False, "error": str(e)} rather than raised, so the Control Plane
can log them uniformly.

**Lines:** 133 | **Size:** 4,769 bytes

## Contains

- **fn** [[core-action_system-executor-py-_run_shell]]`(command, timeout) → dict[str, Any]`
- **fn** [[core-action_system-executor-py-_execute_shell_command]]`(action) → dict[str, Any]`
- **fn** [[core-action_system-executor-py-_execute_run_script]]`(action) → dict[str, Any]`
- **fn** [[core-action_system-executor-py-_execute_write_file]]`(action) → dict[str, Any]`
- **fn** [[core-action_system-executor-py-_execute_call_api]]`(action) → dict[str, Any]`
- **fn** [[core-action_system-executor-py-_execute_compose_action]]`(action) → dict[str, Any]`
- **fn** [[core-action_system-executor-py-execute_action]]`(action) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import os
import subprocess
from typing import Any
from actions import Action
```
