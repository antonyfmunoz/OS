---
type: codebase-file
path: core/objective.py
module: core.objective
lines: 231
size: 7673
generated: 2026-05-07
---

# core/objective.py

Objective Function System — define TRUE success outside the system.

Objectives are real-world success metrics that override internal scoring.
The system can score its own pipeline execution, but only an Objective
knows whether the real world improved.
...

**Lines:** 231 | **Size:** 7,673 bytes

## Depends On

- [[core-orchestrator-pipeline-py]]

## Contains

- **class** [[core-objective-py-Objective]] — 1 methods
- **class** [[core-objective-py-ObjectiveScore]] — 1 methods
- **fn** [[core-objective-py-reply_rate_metric]]`(result, data) → float`
- **fn** [[core-objective-py-engagement_rate_metric]]`(result, data) → float`
- **fn** [[core-objective-py-conversion_rate_metric]]`(result, data) → float`
- **fn** [[core-objective-py-revenue_metric]]`(result, data) → float`
- **fn** [[core-objective-py-register_objective]]`(objective) → None`
- **fn** [[core-objective-py-get_objective]]`(name) → Objective | None`
- **fn** [[core-objective-py-evaluate_objective]]`(result, real_data, objective) → ObjectiveScore`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Callable
from core.orchestrator.pipeline import PipelineResult
```
