---
type: codebase-file
path: scripts/goals.py
module: scripts.goals
lines: 110
size: 2909
tags: [entry-point]
generated: 2026-05-07
---

# scripts/goals.py

> **ENTRY POINT** — Contains `if __name__` or server start.

CLI entry points for goal management. Wraps eos_ai/goal_selector.py.

**Lines:** 110 | **Size:** 2,909 bytes

## Depends On

- [[eos_ai-goal_selector-py]]

## Contains

- **fn** [[scripts-goals-py-_sel]]`() → GoalSelector`
- **fn** [[scripts-goals-py-cmd_goals]]`()`
- **fn** [[scripts-goals-py-cmd_goal_add]]`(title, priority, impact, cost, confidence, venture)`
- **fn** [[scripts-goals-py-cmd_goal_activate]]`(goal_id)`
- **fn** [[scripts-goals-py-cmd_goal_defer]]`(goal_id)`
- **fn** [[scripts-goals-py-cmd_goal_cycle]]`()`
- **fn** [[scripts-goals-py-cmd_goal_explain]]`(goal_id)`

## Import Statements

```python
import os
import sys
from eos_ai.goal_selector import GoalSelector
from eos_ai.goal_selector import GoalState
import json
```
