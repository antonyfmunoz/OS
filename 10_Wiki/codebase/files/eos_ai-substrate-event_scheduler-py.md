---
type: codebase-file
path: eos_ai/substrate/event_scheduler.py
module: eos_ai.substrate.event_scheduler
lines: 352
size: 12987
generated: 2026-05-07
---

# eos_ai/substrate/event_scheduler.py

Event-driven scheduler for lifecycle execution.

Phase 3 of the event-sourced runtime: replaces pull-based orchestration
with event emission → routing → guard evaluation → handler execution.

...

**Lines:** 352 | **Size:** 12,987 bytes

## Used By

- [[eos_ai-substrate-decision_engine-py]]
- [[eos_ai-substrate-execution_authority-py]]
- [[eos_ai-substrate-execution_events-py]]
- [[eos_ai-substrate-execution_result_handler-py]]
- [[eos_ai-substrate-execution_worker-py]]
- [[eos_ai-substrate-llm_decision_events-py]]
- [[eos_ai-substrate-llm_replay-py]]

## Contains

- **class** [[eos_ai-substrate-event_scheduler-py-NonMutatingEventViolation]] — 0 methods
- **class** [[eos_ai-substrate-event_scheduler-py-SchedulerEvent]] — 1 methods
- **class** [[eos_ai-substrate-event_scheduler-py-ExecutionResult]] — 0 methods
- **class** [[eos_ai-substrate-event_scheduler-py-Subscription]] — 0 methods
- **class** [[eos_ai-substrate-event_scheduler-py-RouteResult]] — 0 methods
- **class** [[eos_ai-substrate-event_scheduler-py-RunResult]] — 0 methods
- **class** [[eos_ai-substrate-event_scheduler-py-EventScheduler]] — 7 methods
- **fn** [[eos_ai-substrate-event_scheduler-py-register_event_schema_source]]`(registry) → None`
- **fn** [[eos_ai-substrate-event_scheduler-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-event_scheduler-py-_utcnow]]`() → str`

## Import Statements

```python
from __future__ import annotations
import sys
import threading
import uuid
from collections import deque
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Callable
from typing import Protocol
from eos_ai.substrate.event_log_runtime import EventLogRuntime
from eos_ai.substrate.runtime_state_store import RuntimeStateStore
```
