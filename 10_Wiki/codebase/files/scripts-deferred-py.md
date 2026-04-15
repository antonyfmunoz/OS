---
type: codebase-file
path: scripts/deferred.py
module: scripts.deferred
lines: 349
size: 10691
tags: [entry-point]
generated: 2026-04-12
---

# scripts/deferred.py

> **ENTRY POINT** — Contains `if __name__` or server start.

deferred.py — operator CLI for the Control Plane deferred queue.

Commands:
    list                      show all currently deferred actions
    show <action_id>          print the full persisted action record
...

**Lines:** 349 | **Size:** 10,691 bytes

## Depends On

- [[core-action_system-actions-py]]
- [[core-action_system-control_plane-py]]
- [[core-action_system-deferred-py]]
- [[core-action_system-deferred_status-py]]

## Contains

- **fn** [[scripts-deferred-py-cmd_list]]`(args) → int`
- **fn** [[scripts-deferred-py-cmd_show]]`(args) → int`
- **fn** [[scripts-deferred-py-cmd_approve]]`(args) → int`
- **fn** [[scripts-deferred-py-cmd_drop]]`(args) → int`
- **fn** [[scripts-deferred-py-cmd_status]]`(args) → int`
- **fn** [[scripts-deferred-py-cmd_stale_check]]`(args) → int`
- **fn** [[scripts-deferred-py-cmd_prune]]`(args) → int`
- **fn** [[scripts-deferred-py-cmd_wake]]`(args) → int`
- **fn** [[scripts-deferred-py-_render_sentinel]]`(s) → dict`
- **fn** [[scripts-deferred-py-cmd_idem_list]]`(args) → int`
- **fn** [[scripts-deferred-py-cmd_idem_show]]`(args) → int`
- **fn** [[scripts-deferred-py-cmd_idem_clear]]`(args) → int`
- **fn** [[scripts-deferred-py-cmd_idem_prune]]`(_args) → int`
- **fn** [[scripts-deferred-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from core.action_system.control_plane import list_deferred
from core.action_system.control_plane import load_deferred
from core.action_system.control_plane import resume_action
from core.action_system.deferred import delete_deferred
from core.action_system import idempotency
from core.action_system.deferred_status import DEFAULT_STALE_HOURS
from core.action_system.deferred_status import VALID_STATUSES
from core.action_system.deferred_status import clear_status
from core.action_system.deferred_status import list_overdue_snoozed
from core.action_system.deferred_status import mark_stale_over_threshold
from core.action_system.deferred_status import read_status
from core.action_system.deferred_status import wake_due_snoozed
from core.action_system.deferred_status import write_status
```
