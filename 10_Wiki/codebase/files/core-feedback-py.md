---
type: codebase-file
path: core/feedback.py
module: core.feedback
lines: 386
size: 13249
generated: 2026-05-07
---

# core/feedback.py

Feedback → Primitive Learning Loop.

Converts execution results (PipelineResult) into primitive-level
feedback signals, then applies that feedback to produce improved
primitive compositions.
...

**Lines:** 386 | **Size:** 13,249 bytes

## Depends On

- [[core-orchestrator-pipeline-py]]
- [[core-primitives-py]]
- [[core-transformer-py]]

## Contains

- **class** [[core-feedback-py-PrimitiveEffectiveness]] — 1 methods
- **class** [[core-feedback-py-FeedbackSignal]] — 1 methods
- **fn** [[core-feedback-py-_get_step_primitives]]`(step) → set[PrimitiveTag]`
- **fn** [[core-feedback-py-_compute_step_score]]`(step) → float`
- **fn** [[core-feedback-py-evaluate_result]]`(result, context) → FeedbackSignal`
- **fn** [[core-feedback-py-apply_feedback]]`(primitives, feedback, objective) → tuple[set[PrimitiveTag], TransformationResult]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from core.orchestrator.pipeline import PipelineResult
from core.orchestrator.pipeline import StepOutcome
from core.primitives import L0
from core.primitives import PrimitiveTag
from core.transformer import TransformationResult
from core.transformer import transform
```
