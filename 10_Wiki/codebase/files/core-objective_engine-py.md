---
type: codebase-file
path: core/objective_engine.py
module: core.objective_engine
lines: 417
size: 14257
generated: 2026-05-07
---

# core/objective_engine.py

Multi-Objective Engine — evaluate runs against multiple weighted objectives.

Extends the single-objective system in core/objective.py to support:
- Multiple simultaneous objectives with weights
- Hard constraints that override weighted scoring
...

**Lines:** 417 | **Size:** 14,257 bytes

## Contains

- **class** [[core-objective_engine-py-ObjectiveFunction]] — 3 methods
- **class** [[core-objective_engine-py-ObjectiveResult]] — 1 methods
- **class** [[core-objective_engine-py-ObjectiveSet]] — 6 methods
- **fn** [[core-objective_engine-py-outreach_objectives]]`() → ObjectiveSet`
- **fn** [[core-objective_engine-py-content_objectives]]`() → ObjectiveSet`
- **fn** [[core-objective_engine-py-habit_objectives]]`() → ObjectiveSet`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
```
