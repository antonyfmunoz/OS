---
type: codebase-file
path: eos_ai/execution_loop.py
module: eos_ai.execution_loop
lines: 322
size: 11524
tags: [entry-point]
generated: 2026-05-07
---

# eos_ai/execution_loop.py

> **ENTRY POINT** — Contains `if __name__` or server start.

ExecutionLoop — closed-loop goal execution with outcome feedback.

The reality bridge: connects goal selection → planning → execution →
outcome recording → automatic reselection into a single deterministic
cycle.
...

**Lines:** 322 | **Size:** 11,524 bytes

## Depends On

- [[eos_ai-goal_selector-py]]

## Contains

- **class** [[eos_ai-execution_loop-py-ExecutionResult]] — 0 methods
- **class** [[eos_ai-execution_loop-py-Executor]] — 1 methods
- **class** [[eos_ai-execution_loop-py-Planner]] — 1 methods
- **class** [[eos_ai-execution_loop-py-PassthroughPlanner]] — 1 methods
- **class** [[eos_ai-execution_loop-py-NoOpExecutor]] — 1 methods
- **class** [[eos_ai-execution_loop-py-CycleResult]] — 0 methods
- **class** [[eos_ai-execution_loop-py-ExecutionLoop]] — 7 methods
- **fn** [[eos_ai-execution_loop-py-_safe_serialize]]`(obj) → Any`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
import time
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Callable
from typing import Protocol
from eos_ai.goal_selector import Goal
from eos_ai.goal_selector import GoalSelector
from eos_ai.goal_selector import GoalState
from eos_ai.goal_selector import OutcomeTracker
```
