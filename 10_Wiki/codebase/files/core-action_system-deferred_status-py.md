---
type: codebase-file
path: core/action_system/deferred_status.py
module: core.action_system.deferred_status
lines: 242
size: 7983
generated: 2026-04-11
---

# core/action_system/deferred_status.py

Lightweight status tracking for deferred actions.

Status is stored as a sidecar JSON file next to each deferred action:

    /opt/OS/logs/deferred/<action_id>.json          # the action
...

**Lines:** 242 | **Size:** 7,983 bytes

## Used By

- [[scripts-deferred-py]]

## Contains

- **class** [[core-action_system-deferred_status-py-DeferredStatus]] — 1 methods
- **fn** [[core-action_system-deferred_status-py-_status_path]]`(action_id) → str`
- **fn** [[core-action_system-deferred_status-py-read_status]]`(action_id) → DeferredStatus`
- **fn** [[core-action_system-deferred_status-py-write_status]]`(action_id, status) → DeferredStatus`
- **fn** [[core-action_system-deferred_status-py-clear_status]]`(action_id) → bool`
- **fn** [[core-action_system-deferred_status-py-is_stale]]`(deferred_at) → bool`
- **fn** [[core-action_system-deferred_status-py-wake_due_snoozed]]`(now) → list[str]`
- **fn** [[core-action_system-deferred_status-py-list_overdue_snoozed]]`(now) → list[str]`
- **fn** [[core-action_system-deferred_status-py-mark_stale_over_threshold]]`(threshold_hours) → list[str]`

## Import Statements

```python
from __future__ import annotations
import json
import os
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from deferred import DEFERRED_DIR
```
