---
type: codebase-file
path: eos_ai/runtime/work_state.py
module: eos_ai.runtime.work_state
lines: 221
size: 6715
generated: 2026-05-07
---

# eos_ai/runtime/work_state.py

Work State Detection + Idle Gate + Adaptive Throttling.

Determines whether the system has meaningful work to do, and controls
sleep duration based on load and provider health.  Consumers call
``get_idle_delay()`` to learn how long to sleep before the next cycle.
...

**Lines:** 221 | **Size:** 6,715 bytes

## Contains

- **class** [[eos_ai-runtime-work_state-py-Pressure]] — 0 methods
- **class** [[eos_ai-runtime-work_state-py-WorkState]] — 1 methods
- **fn** [[eos_ai-runtime-work_state-py-record_signal]]`() → None`
- **fn** [[eos_ai-runtime-work_state-py-has_recent_signal]]`() → bool`
- **fn** [[eos_ai-runtime-work_state-py-_measure_pressure]]`() → Pressure`
- **fn** [[eos_ai-runtime-work_state-py-_get_swap_pct]]`() → float`
- **fn** [[eos_ai-runtime-work_state-py-_compute_idle_delay]]`(pressure, is_idle) → float`
- **fn** [[eos_ai-runtime-work_state-py-reset_idle_counter]]`() → None`
- **fn** [[eos_ai-runtime-work_state-py-register_goal_detector]]`(fn) → None`
- **fn** [[eos_ai-runtime-work_state-py-register_task_detector]]`(fn) → None`
- **fn** [[eos_ai-runtime-work_state-py-detect_work_state]]`() → WorkState`
- **fn** [[eos_ai-runtime-work_state-py-get_idle_delay]]`() → float`

## Import Statements

```python
from __future__ import annotations
import os
import time
import logging
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Callable
```
