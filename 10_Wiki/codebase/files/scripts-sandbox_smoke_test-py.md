---
type: codebase-file
path: scripts/sandbox_smoke_test.py
module: scripts.sandbox_smoke_test
lines: 293
size: 9985
tags: [entry-point]
generated: 2026-05-07
---

# scripts/sandbox_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

sandbox_smoke_test.py — End-to-end proof that the sandbox layer works.

Runs, in order:

  1. Create a sandbox, write a file through ActionSystem, confirm
...

**Lines:** 293 | **Size:** 9,985 bytes

## Depends On

- [[core-environment-py]]
- [[core-observability-py]]
- [[scripts-action_system-py]]
- [[scripts-workflow_engine-py]]

## Contains

- **fn** [[scripts-sandbox_smoke_test-py-_step]]`(name, ok, detail) → None`
- **fn** [[scripts-sandbox_smoke_test-py-_fail]]`(name, detail) → None`
- **fn** [[scripts-sandbox_smoke_test-py-step_write_file_in_sandbox]]`() → None`
- **fn** [[scripts-sandbox_smoke_test-py-step_edit_production_hub_in_sandbox]]`() → None`
- **fn** [[scripts-sandbox_smoke_test-py-step_workflow_logs_isolated]]`() → None`
- **fn** [[scripts-sandbox_smoke_test-py-step_orchestrator_tick_in_sandbox]]`() → None`
- **fn** [[scripts-sandbox_smoke_test-py-step_observability_env_views]]`() → None`
- **fn** [[scripts-sandbox_smoke_test-py-step_playground_is_ephemeral]]`() → None`
- **fn** [[scripts-sandbox_smoke_test-py-step_run_safety_verifier]]`() → None`
- **fn** [[scripts-sandbox_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import json
import subprocess
import sys
import time
from pathlib import Path
from core.environment import make_playground
from core.environment import make_sandbox
from core.observability import Observability
from scripts.action_system import ActionSystem
from scripts.action_system import ActionType
from scripts.workflow_engine import WorkflowEngine
from scripts.workflow_engine import build_research_workflow
```
