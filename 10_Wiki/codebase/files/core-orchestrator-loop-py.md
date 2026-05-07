---
type: codebase-file
path: core/orchestrator/loop.py
module: core.orchestrator.loop
lines: 451
size: 15976
generated: 2026-05-07
---

# core/orchestrator/loop.py

Autonomous loop — deterministic orchestration cycle.

One cycle does exactly four things, in order:

  1. Drain pending signals: for each pending emission, dispatch every
...

**Lines:** 451 | **Size:** 15,976 bytes

## Depends On

- [[core-action_system-deferred-py]]
- [[core-action_system-logging-py]]

## Used By

- [[scripts-orchestrator_loop-py]]
- [[scripts-orchestrator_status-py]]

## Contains

- **class** [[core-orchestrator-loop-py-LoopConfig]] — 0 methods
- **class** [[core-orchestrator-loop-py-CycleReport]] — 1 methods
- **fn** [[core-orchestrator-loop-py-_drain_signals]]`(orch, report) → None`
- **fn** [[core-orchestrator-loop-py-_scan_stale_deferred]]`(config, report) → None`
- **fn** [[core-orchestrator-loop-py-_today_execution_log_path]]`() → str`
- **fn** [[core-orchestrator-loop-py-_read_recent_failures]]`(limit) → list[dict[str, Any]]`
- **fn** [[core-orchestrator-loop-py-_already_followed_up]]`(action_id) → bool`
- **fn** [[core-orchestrator-loop-py-_scan_failures]]`(config, report) → None`
- **fn** [[core-orchestrator-loop-py-_write_heartbeat]]`(report, error) → None`
- **fn** [[core-orchestrator-loop-py-run_cycle]]`(orch, config) → CycleReport`
- **fn** [[core-orchestrator-loop-py-run_forever]]`(orch, config, max_cycles) → None`

## Import Statements

```python
from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
from core.action_system.deferred import list_deferred
from core.action_system.logging import DECISION_LOG_DIR
from core.action_system.logging import EXECUTION_LOG_DIR
from core.action_system.logging import log_decision
from orchestrator import Orchestrator
from orchestrator import default_orchestrator
from signals import SignalEmission
from signals import emit_signal
from signals import get_handlers
from signals import list_pending
from signals import list_signals
from signals import mark_processed
```
