---
type: codebase-file
path: eos_ai/substrate/capability_routing.py
module: eos_ai.substrate.capability_routing
lines: 231
size: 7933
generated: 2026-05-07
---

# eos_ai/substrate/capability_routing.py

Capability-aware task routing — deterministic target selection.

Maps tasks to execution targets based on content analysis and session state.
No LLM calls. No network calls. Pure keyword heuristics + session context.

...

**Lines:** 231 | **Size:** 7,933 bytes

## Contains

- **class** [[eos_ai-substrate-capability_routing-py-TaskCapability]] — 0 methods
- **class** [[eos_ai-substrate-capability_routing-py-ExecutionTarget]] — 0 methods
- **fn** [[eos_ai-substrate-capability_routing-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-capability_routing-py-infer_task_capabilities]]`(task) → set[TaskCapability]`
- **fn** [[eos_ai-substrate-capability_routing-py-choose_execution_target]]`(task, session, local_available) → ExecutionTarget`
- **fn** [[eos_ai-substrate-capability_routing-py-route_task]]`(task, session, local_available) → 'Task'`
- **fn** [[eos_ai-substrate-capability_routing-py-_build_reason]]`(caps, target, session, local_available) → str`

## Import Statements

```python
from __future__ import annotations
import re
import sys
from enum import Enum
from typing import TYPE_CHECKING
from typing import Optional
```
