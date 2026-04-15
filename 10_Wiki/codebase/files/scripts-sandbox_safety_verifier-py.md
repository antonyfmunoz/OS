---
type: codebase-file
path: scripts/sandbox_safety_verifier.py
module: scripts.sandbox_safety_verifier
lines: 331
size: 12024
tags: [entry-point]
generated: 2026-04-12
---

# scripts/sandbox_safety_verifier.py

> **ENTRY POINT** — Contains `if __name__` or server start.

sandbox_safety_verifier.py — Adversarial tests for the sandbox boundary.

Proves, end to end, that a sandbox environment CANNOT corrupt
production state under any of the attack shapes we care about:

...

**Lines:** 331 | **Size:** 12,024 bytes

## Depends On

- [[core-environment-py]]
- [[scripts-action_system-py]]
- [[scripts-workflow_engine-py]]

## Contains

- **class** [[scripts-sandbox_safety_verifier-py-Failure]] — 0 methods
- **fn** [[scripts-sandbox_safety_verifier-py-_assert]]`(cond, msg) → None`
- **fn** [[scripts-sandbox_safety_verifier-py-_run]]`(name, fn) → None`
- **fn** [[scripts-sandbox_safety_verifier-py-check_guard_blocks_production_paths]]`() → None`
- **fn** [[scripts-sandbox_safety_verifier-py-check_absolute_path_outside_repo_is_rejected]]`() → None`
- **fn** [[scripts-sandbox_safety_verifier-py-check_sandbox_edit_does_not_touch_production]]`() → None`
- **fn** [[scripts-sandbox_safety_verifier-py-check_sandbox_write_blocked_if_target_outside_workspace]]`() → None`
- **fn** [[scripts-sandbox_safety_verifier-py-check_workflow_logs_land_in_sandbox]]`() → None`
- **fn** [[scripts-sandbox_safety_verifier-py-check_action_logs_tagged_with_env]]`() → None`
- **fn** [[scripts-sandbox_safety_verifier-py-check_cleanup_refuses_random_directories]]`() → None`
- **fn** [[scripts-sandbox_safety_verifier-py-check_graph_refresh_disabled_in_sandbox]]`() → None`
- **fn** [[scripts-sandbox_safety_verifier-py-check_neon_audit_disabled_in_sandbox]]`() → None`
- **fn** [[scripts-sandbox_safety_verifier-py-check_playground_is_ephemeral]]`() → None`
- **fn** [[scripts-sandbox_safety_verifier-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import json
import sys
from pathlib import Path
from core.environment import FORBIDDEN_WRITE_PREFIXES
from core.environment import Environment
from core.environment import make_playground
from core.environment import make_sandbox
from scripts.action_system import ActionSystem
from scripts.action_system import ActionType
from scripts.workflow_engine import WorkflowEngine
from scripts.workflow_engine import build_research_workflow
```
