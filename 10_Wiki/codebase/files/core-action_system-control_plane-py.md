---
type: codebase-file
path: core/action_system/control_plane.py
module: core.action_system.control_plane
lines: 273
size: 10180
generated: 2026-04-11
---

# core/action_system/control_plane.py

Control Plane — the public entry point for the EOS Action System.

Lifecycle:
    propose → validate → approve → execute → log

...

**Lines:** 273 | **Size:** 10,180 bytes

## Depends On

- [[eos_ai-accountability-py]]

## Used By

- [[core-orchestrator-handlers-py]]
- [[core-orchestrator-pipeline-py]]
- [[core-orchestrator-steps-py]]
- [[core-tool_mastery_manager-ensure-py]]
- [[scripts-control_plane_run-py]]
- [[scripts-deferred-py]]

## Contains

- **fn** [[core-action_system-control_plane-py-_execute_approved]]`(action) → Action`
- **fn** [[core-action_system-control_plane-py-_skipped_duplicate]]`() → Action`
- **fn** [[core-action_system-control_plane-py-_deferred_file_exists]]`(action_id) → bool`
- **fn** [[core-action_system-control_plane-py-run_action]]`(type, description) → Action`
- **fn** [[core-action_system-control_plane-py-resume_action]]`(action_id) → Action`

## Import Statements

```python
from __future__ import annotations
import os
import uuid
from typing import Any
from  import idempotency
from actions import Action
from actions import propose_action
from deferred import DEFERRED_DIR
from deferred import delete_deferred
from deferred import list_deferred
from deferred import load_deferred
from deferred import save_deferred
from executor import execute_action
from logging import log_decision
from logging import log_execution
from notifier import Notifier
from notifier import default_notifier
from policy import resolve_effective_risk
from tme import query_relevant_skills
from validator import approve_action
from validator import validate_action
```
