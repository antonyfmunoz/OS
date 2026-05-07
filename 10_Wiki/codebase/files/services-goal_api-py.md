---
type: codebase-file
path: services/goal_api.py
module: services.goal_api
lines: 195
size: 6387
tags: [entry-point]
generated: 2026-05-07
---

# services/goal_api.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Goal API — REST endpoints for goal selection + focus management.

Endpoints:
    GET  /goals              — list all goals (optional ?state= filter)
    POST /goals              — create a goal
...

**Lines:** 195 | **Size:** 6,387 bytes

## Depends On

- [[eos_ai-goal_selector-py]]

## Contains

- **fn** [[services-goal_api-py-_selector]]`() → GoalSelector`
- **fn** [[services-goal_api-py-_goal_to_dict]]`(goal) → dict`
- **fn** [[services-goal_api-py-list_goals]]`()`
- **fn** [[services-goal_api-py-create_goal]]`()`
- **fn** [[services-goal_api-py-get_goal]]`(goal_id)`
- **fn** [[services-goal_api-py-activate_goal]]`(goal_id)`
- **fn** [[services-goal_api-py-defer_goal]]`(goal_id)`
- **fn** [[services-goal_api-py-complete_goal]]`(goal_id)`
- **fn** [[services-goal_api-py-drop_goal]]`(goal_id)`
- **fn** [[services-goal_api-py-run_cycle]]`()`
- **fn** [[services-goal_api-py-health]]`()`
- **fn** [[services-goal_api-py-register]]`(flask_app) → None`

## Import Statements

```python
import os
import sys
from flask import Flask
from flask import request
from flask import jsonify
from eos_ai.goal_selector import GoalSelector
from eos_ai.goal_selector import GoalState
```
