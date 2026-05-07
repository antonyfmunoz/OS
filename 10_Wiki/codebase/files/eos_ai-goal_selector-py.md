---
type: codebase-file
path: eos_ai/goal_selector.py
module: eos_ai.goal_selector
lines: 1556
size: 61244
tags: [entry-point]
generated: 2026-05-07
---

# eos_ai/goal_selector.py

> **ENTRY POINT** — Contains `if __name__` or server start.

GoalSelector — goal selection + system focus layer (Phase 9D + 9E + 9F).

Determines WHICH goals the system pursues, not how to execute them.
Goals compete for attention through a weighted scoring model.
Only ACTIVE goals produce tasks — everything else is silent.
...

**Lines:** 1556 | **Size:** 61,244 bytes

## Depends On

- [[eos_ai-db-py]]

## Used By

- [[eos_ai-execution_loop-py]]
- [[scripts-goals-py]]
- [[services-goal_api-py]]

## Contains

- **class** [[eos_ai-goal_selector-py-GoalState]] — 0 methods
- **class** [[eos_ai-goal_selector-py-PerformanceProfile]] — 3 methods
- **class** [[eos_ai-goal_selector-py-MultiHorizonProfile]] — 5 methods
- **class** [[eos_ai-goal_selector-py-Goal]] — 0 methods
- **class** [[eos_ai-goal_selector-py-OpportunityCostLayer]] — 4 methods
- **class** [[eos_ai-goal_selector-py-StrategicHorizonLayer]] — 5 methods
- **class** [[eos_ai-goal_selector-py-GoalSelector]] — 22 methods
- **class** [[eos_ai-goal_selector-py-OutcomeTracker]] — 11 methods

## Import Statements

```python
import json
import math
import os
import sys
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Optional
from eos_ai.db import get_conn
from eos_ai.db import ORG_ID
```
