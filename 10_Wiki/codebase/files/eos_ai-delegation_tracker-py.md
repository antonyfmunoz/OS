---
type: codebase-file
path: eos_ai/delegation_tracker.py
module: eos_ai.delegation_tracker
lines: 101
size: 3230
generated: 2026-04-11
---

# eos_ai/delegation_tracker.py

Delegation Tracker — tracks tasks routed to CEO agents
or other parties. Follows up if not completed.

**Lines:** 101 | **Size:** 3,230 bytes

## Contains

- **fn** [[eos_ai-delegation_tracker-py-log_delegation]]`(task, delegated_to, due_hours, ctx) → bool`
- **fn** [[eos_ai-delegation_tracker-py-get_overdue_delegations]]`(ctx) → list[dict]`
- **fn** [[eos_ai-delegation_tracker-py-mark_delegation_complete]]`(event_id, ctx) → bool`

## Import Statements

```python
import json
import logging
from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo
```
