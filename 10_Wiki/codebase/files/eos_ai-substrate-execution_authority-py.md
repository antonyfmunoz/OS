---
type: codebase-file
path: eos_ai/substrate/execution_authority.py
module: eos_ai.substrate.execution_authority
lines: 496
size: 16229
generated: 2026-05-07
---

# eos_ai/substrate/execution_authority.py

Event-primary execution authority for lifecycle transitions.

Phase 4: Authority transfer. This module provides the scheduler-driven
execution path for every lifecycle transition. When ExecutionMode is
EVENT_PRIMARY, run_lifecycle.py routes calls here instead of through
...

**Lines:** 496 | **Size:** 16,229 bytes

## Depends On

- [[eos_ai-substrate-event_scheduler-py]]
- [[eos_ai-substrate-execution_contract-py]]
- [[eos_ai-substrate-execution_events-py]]
- [[eos_ai-substrate-execution_router-py]]

## Contains

- **class** [[eos_ai-substrate-execution_authority-py-ExecutionAuthorityError]] — 0 methods
- **class** [[eos_ai-substrate-execution_authority-py-EventPrimaryResult]] — 0 methods
- **class** [[eos_ai-substrate-execution_authority-py-ExecutionAuthority]] — 2 methods
- **fn** [[eos_ai-substrate-execution_authority-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-execution_authority-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-execution_authority-py-_get_primary_scheduler]]`() → tuple[EventScheduler, RuntimeStateStore]`
- **fn** [[eos_ai-substrate-execution_authority-py-_emit_and_drain]]`(event_type, session_name, source, run_id, payload, metadata) → EventPrimaryResult`
- **fn** [[eos_ai-substrate-execution_authority-py-event_primary_propose_completion]]`(session_name, source) → EventPrimaryResult`
- **fn** [[eos_ai-substrate-execution_authority-py-event_primary_finalize]]`(session_name, source, finalize_fn) → EventPrimaryResult`
- **fn** [[eos_ai-substrate-execution_authority-py-event_primary_record_publication]]`(session_name, source) → EventPrimaryResult`
- **fn** [[eos_ai-substrate-execution_authority-py-event_primary_request_clear]]`(session_name, source) → EventPrimaryResult`
- **fn** [[eos_ai-substrate-execution_authority-py-event_primary_confirm_clear]]`(session_name, source) → EventPrimaryResult`
- **fn** [[eos_ai-substrate-execution_authority-py-event_primary_mark_terminal]]`(session_name, source) → EventPrimaryResult`
- **fn** [[eos_ai-substrate-execution_authority-py-event_primary_full_lifecycle]]`(session_name, source, finalize_fn) → EventPrimaryResult`
- **fn** [[eos_ai-substrate-execution_authority-py-reset_for_testing]]`() → None`

## Import Statements

```python
from __future__ import annotations
import sys
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Callable
from eos_ai.substrate.event_scheduler import EventScheduler
from eos_ai.substrate.event_scheduler import ExecutionResult as SchedulerExecutionResult
from eos_ai.substrate.event_scheduler import RunResult
from eos_ai.substrate.event_scheduler import SchedulerEvent
from eos_ai.substrate.execution_contract import ExecutionClass
from eos_ai.substrate.execution_contract import ExecutionConstraints
from eos_ai.substrate.execution_contract import ExecutionRequest
from eos_ai.substrate.execution_contract import RoutingContext
from eos_ai.substrate.execution_contract import _compute_idempotency_key
from eos_ai.substrate.execution_contract import _new_execution_id
from eos_ai.substrate.execution_events import build_execution_requested_event
from eos_ai.substrate.execution_router import ExecutionRouter
from eos_ai.substrate.lifecycle_handlers import create_lifecycle_scheduler
from eos_ai.substrate.runtime_state_store import RuntimeStateStore
```
