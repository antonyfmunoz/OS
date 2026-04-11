---
type: codebase-file
path: scripts/orchestrator_status.py
module: scripts.orchestrator_status
lines: 389
size: 12290
tags: [entry-point]
generated: 2026-04-11
---

# scripts/orchestrator_status.py

> **ENTRY POINT** — Contains `if __name__` or server start.

orchestrator_status.py — operator-friendly snapshot of the Control Plane.

Prints five sections in a compact human-readable format:

  1. Pending signals (per signal name + count + oldest emission age)
...

**Lines:** 389 | **Size:** 12,290 bytes

## Depends On

- [[core-action_system-deferred-py]]
- [[core-action_system-logging-py]]
- [[core-orchestrator-loop-py]]
- [[core-orchestrator-orchestrator-py]]
- [[core-orchestrator-signals-py]]
- [[core-orchestrator-workflows-py]]

## Contains

- **fn** [[scripts-orchestrator_status-py-_now]]`() → datetime`
- **fn** [[scripts-orchestrator_status-py-_age_seconds]]`(iso) → int | None`
- **fn** [[scripts-orchestrator_status-py-_fmt_age]]`(seconds) → str`
- **fn** [[scripts-orchestrator_status-py-_today_execution_log]]`() → str`
- **fn** [[scripts-orchestrator_status-py-pending_signals_summary]]`() → list[dict[str, Any]]`
- **fn** [[scripts-orchestrator_status-py-deferred_summary]]`() → dict[str, Any]`
- **fn** [[scripts-orchestrator_status-py-recent_workflows]]`() → list[dict[str, Any]]`
- **fn** [[scripts-orchestrator_status-py-recent_failures]]`(limit) → list[dict[str, Any]]`
- **fn** [[scripts-orchestrator_status-py-loop_heartbeat]]`() → dict[str, Any]`
- **fn** [[scripts-orchestrator_status-py-loop_activity]]`() → dict[str, Any]`
- **fn** [[scripts-orchestrator_status-py-_hdr]]`(title) → str`
- **fn** [[scripts-orchestrator_status-py-render_text]]`(snapshot) → str`
- **fn** [[scripts-orchestrator_status-py-build_snapshot]]`() → dict[str, Any]`
- **fn** [[scripts-orchestrator_status-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import os
import sys
from datetime import datetime
from datetime import timezone
from typing import Any
from core.action_system.deferred import list_deferred
from core.action_system.logging import DECISION_LOG_DIR
from core.action_system.logging import EXECUTION_LOG_DIR
from core.orchestrator.loop import HEARTBEAT_PATH
from core.orchestrator.orchestrator import STATE_PATH
from core.orchestrator.orchestrator import default_orchestrator
from core.orchestrator.signals import get_handlers
from core.orchestrator.signals import list_pending
from core.orchestrator.signals import list_signals
from core.orchestrator.workflows import register_default_workflows
```
