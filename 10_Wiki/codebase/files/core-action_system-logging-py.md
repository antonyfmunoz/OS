---
type: codebase-file
path: core/action_system/logging.py
module: core.action_system.logging
lines: 73
size: 2246
generated: 2026-04-12
---

# core/action_system/logging.py

Append-only JSONL loggers for execution and decision records.

Two logs, two directories, one record per line. Simple to `tail -f`,
simple to grep, simple to replay.

**Lines:** 73 | **Size:** 2,246 bytes

## Used By

- [[core-orchestrator-decisions-py]]
- [[core-orchestrator-loop-py]]
- [[core-orchestrator-orchestrator-py]]
- [[core-orchestrator-pipeline-py]]
- [[scripts-force_execution_loop-py]]
- [[scripts-orchestrator_status-py]]

## Contains

- **fn** [[core-action_system-logging-py-_today_path]]`(directory, stem) → str`
- **fn** [[core-action_system-logging-py-_append_jsonl]]`(path, record) → None`
- **fn** [[core-action_system-logging-py-log_execution]]`(action, result) → str`
- **fn** [[core-action_system-logging-py-log_decision]]`(context, options_considered, chosen_option, reasoning) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import json
import os
import uuid
from datetime import datetime
from datetime import timezone
from typing import Any
from actions import Action
```
