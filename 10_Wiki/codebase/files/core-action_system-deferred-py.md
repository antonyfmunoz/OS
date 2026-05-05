---
type: codebase-file
path: core/action_system/deferred.py
module: core.action_system.deferred
lines: 97
size: 3086
generated: 2026-04-12
---

# core/action_system/deferred.py

Durable persistence for deferred actions.

When a medium/high-risk action passes validation but has no explicit
approval, the Control Plane defers it. Deferred actions are persisted
as one JSON file per action under /opt/OS/logs/deferred/ so they can
...

**Lines:** 97 | **Size:** 3,086 bytes

## Used By

- [[core-orchestrator-loop-py]]
- [[scripts-deferred-py]]
- [[scripts-orchestrator_status-py]]

## Contains

- **fn** [[core-action_system-deferred-py-_path_for]]`(action_id) → str`
- **fn** [[core-action_system-deferred-py-save_deferred]]`(action) → str`
- **fn** [[core-action_system-deferred-py-load_deferred]]`(action_id) → Action`
- **fn** [[core-action_system-deferred-py-delete_deferred]]`(action_id) → bool`
- **fn** [[core-action_system-deferred-py-list_deferred]]`() → list[dict[str, Any]]`

## Import Statements

```python
from __future__ import annotations
import json
import os
from dataclasses import fields
from datetime import datetime
from datetime import timezone
from typing import Any
from actions import Action
```
