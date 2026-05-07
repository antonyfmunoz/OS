---
type: codebase-file
path: core/dynamics.py
module: core.dynamics
lines: 271
size: 9442
generated: 2026-05-07
---

# core/dynamics.py

Feedback Dynamics — model delayed, nonlinear, and compounding outcomes.

Real-world outcomes are rarely immediate or linear:
- Content may convert viewers days later
- Outreach replies arrive over a week
...

**Lines:** 271 | **Size:** 9,442 bytes

## Contains

- **class** [[core-dynamics-py-FeedbackDynamics]] — 8 methods
- **class** [[core-dynamics-py-DelayedScore]] — 2 methods
- **fn** [[core-dynamics-py-outreach_dynamics]]`() → FeedbackDynamics`
- **fn** [[core-dynamics-py-content_dynamics]]`() → FeedbackDynamics`
- **fn** [[core-dynamics-py-habit_dynamics]]`() → FeedbackDynamics`

## Import Statements

```python
from __future__ import annotations
import math
from dataclasses import dataclass
from dataclasses import field
from typing import Any
```
