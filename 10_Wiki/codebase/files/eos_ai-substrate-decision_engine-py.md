---
type: codebase-file
path: eos_ai/substrate/decision_engine.py
module: eos_ai.substrate.decision_engine
lines: 311
size: 10364
generated: 2026-05-07
---

# eos_ai/substrate/decision_engine.py

Decision engine — control-plane cognition layer.

Reads RuntimeStateStore (read-only), evaluates a pluggable strategy,
and produces a DecisionOutput that the scheduler can emit as an event.
The engine NEVER executes anything directly.
...

**Lines:** 311 | **Size:** 10,364 bytes

## Depends On

- [[eos_ai-substrate-event_scheduler-py]]

## Used By

- [[eos_ai-substrate-llm_replay-py]]
- [[eos_ai-substrate-planner-py]]

## Contains

- **class** [[eos_ai-substrate-decision_engine-py-DecisionOutput]] — 2 methods
- **class** [[eos_ai-substrate-decision_engine-py-DecisionStrategy]] — 2 methods
- **class** [[eos_ai-substrate-decision_engine-py-Rule]] — 0 methods
- **class** [[eos_ai-substrate-decision_engine-py-RuleBasedStrategy]] — 5 methods
- **class** [[eos_ai-substrate-decision_engine-py-DecisionEngine]] — 7 methods
- **fn** [[eos_ai-substrate-decision_engine-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-decision_engine-py-_compute_state_hash]]`(state) → str`
- **fn** [[eos_ai-substrate-decision_engine-py-evaluate_and_emit]]`(engine, store, scheduler) → DecisionOutput | None`

## Import Statements

```python
from __future__ import annotations
import hashlib
import json
import sys
import uuid
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Protocol
from eos_ai.substrate.decision_events import build_decision_made_event
from eos_ai.substrate.event_scheduler import SchedulerEvent
from eos_ai.substrate.runtime_state_store import RuntimeStateStore
```
