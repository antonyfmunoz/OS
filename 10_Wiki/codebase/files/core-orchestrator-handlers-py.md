---
type: codebase-file
path: core/orchestrator/handlers.py
module: core.orchestrator.handlers
lines: 322
size: 11279
generated: 2026-04-12
---

# core/orchestrator/handlers.py

Signal handler workflows.

Each handler is a plain callable `(context: dict) -> dict` that the
orchestrator can run via `run_workflow()`. The context passed by the
loop has shape:
...

**Lines:** 322 | **Size:** 11,279 bytes

## Depends On

- [[core-action_system-control_plane-py]]
- [[core-action_system-notifier-py]]

## Contains

- **fn** [[core-orchestrator-handlers-py-_append_operator_notice]]`() → dict[str, Any]`
- **fn** [[core-orchestrator-handlers-py-_action_from_context]]`(context) → dict[str, Any]`
- **fn** [[core-orchestrator-handlers-py-handle_deferred_stale]]`(context) → dict[str, Any]`
- **fn** [[core-orchestrator-handlers-py-handle_action_failed]]`(context) → dict[str, Any]`
- **fn** [[core-orchestrator-handlers-py-handle_action_retry_requested]]`(context) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import json
import os
from datetime import datetime
from datetime import timezone
from typing import Any
from core.action_system.control_plane import log_decision
from core.action_system.control_plane import run_action
from core.action_system.notifier import NOTIFICATION_QUEUE
from decisions import should_escalate
from decisions import should_ignore
from decisions import should_retry
```
