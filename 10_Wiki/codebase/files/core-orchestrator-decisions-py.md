---
type: codebase-file
path: core/orchestrator/decisions.py
module: core.orchestrator.decisions
lines: 159
size: 5228
generated: 2026-04-12
---

# core/orchestrator/decisions.py

Decision helpers for signal handler workflows.

These are tiny, deterministic predicates that inspect an action dict
(as it appears in an execution log record or a signal payload) and
answer one question each:
...

**Lines:** 159 | **Size:** 5,228 bytes

## Depends On

- [[core-action_system-logging-py]]

## Contains

- **fn** [[core-orchestrator-decisions-py-_today_decision_log_path]]`() → str`
- **fn** [[core-orchestrator-decisions-py-retry_count_today]]`(action_id) → int`
- **fn** [[core-orchestrator-decisions-py-_action_type]]`(action) → str`
- **fn** [[core-orchestrator-decisions-py-_risk]]`(action) → str`
- **fn** [[core-orchestrator-decisions-py-_has_idempotency]]`(action) → bool`
- **fn** [[core-orchestrator-decisions-py-should_retry]]`(action) → bool`
- **fn** [[core-orchestrator-decisions-py-should_escalate]]`(action) → bool`
- **fn** [[core-orchestrator-decisions-py-should_ignore]]`(action) → bool`

## Import Statements

```python
from __future__ import annotations
import json
import os
from datetime import datetime
from datetime import timezone
from typing import Any
from core.action_system.logging import DECISION_LOG_DIR
```
