---
type: codebase-file
path: scripts/force_execution_loop.py
module: scripts.force_execution_loop
lines: 309
size: 11848
tags: [entry-point]
generated: 2026-05-07
---

# scripts/force_execution_loop.py

> **ENTRY POINT** — Contains `if __name__` or server start.

force_execution_loop.py — Force ONE complete end-to-end execution loop.

This is the activation script. It proves the full pipeline works:

    intent → workflow → action → logging → feedback → optimizer
...

**Lines:** 309 | **Size:** 11,848 bytes

## Depends On

- [[core-action_system-control_plane-py]]
- [[core-action_system-logging-py]]
- [[core-optimizer-py]]
- [[eos_ai-workflow_engine-py]]

## Contains

- **fn** [[scripts-force_execution_loop-py-_append_jsonl]]`(path, record) → None`
- **fn** [[scripts-force_execution_loop-py-_ts]]`() → str`
- **fn** [[scripts-force_execution_loop-py-step_generate_outreach_message]]`() → tuple[bool, dict]`
- **fn** [[scripts-force_execution_loop-py-step_save_outreach_to_file]]`(message_data) → tuple[bool, dict]`
- **fn** [[scripts-force_execution_loop-py-step_verify_output]]`(saved_path) → tuple[bool, dict]`
- **fn** [[scripts-force_execution_loop-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import json
import sys
import time
from datetime import datetime
from datetime import timezone
from pathlib import Path
from core.action_system.control_plane import run_action
from core.action_system.logging import log_decision
from core.optimizer import Optimizer
from eos_ai.workflow_engine import WorkflowEngine
from eos_ai.workflow_engine import WorkflowState
from eos_ai.workflow_engine import WORKFLOWS
```
