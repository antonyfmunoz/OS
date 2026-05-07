---
type: codebase-file
path: core/transformer.py
module: core.transformer
lines: 338
size: 12199
generated: 2026-05-07
---

# core/transformer.py

Primitive Transformation Engine — restructures primitive compositions.

Given a set of primitives, an objective, and constraints, the transformer
analyses the composition for gaps and inefficiencies then returns an
improved primitive set.  It never mutates the input, never introduces new
...

**Lines:** 338 | **Size:** 12,199 bytes

## Depends On

- [[core-primitives-py]]

## Used By

- [[core-feedback-py]]
- [[core-self_improvement-py]]

## Contains

- **class** [[core-transformer-py-TransformationResult]] — 4 methods
- **fn** [[core-transformer-py-_rule_ensure_goal_action]]`(tags, objective, constraints) → tuple[set[PrimitiveTag], list[str]]`
- **fn** [[core-transformer-py-_rule_feedback_loop]]`(tags, objective, constraints) → tuple[set[PrimitiveTag], list[str]]`
- **fn** [[core-transformer-py-_rule_state_tracking]]`(tags, objective, constraints) → tuple[set[PrimitiveTag], list[str]]`
- **fn** [[core-transformer-py-_rule_outcome_closure]]`(tags, objective, constraints) → tuple[set[PrimitiveTag], list[str]]`
- **fn** [[core-transformer-py-_rule_resource_awareness]]`(tags, objective, constraints) → tuple[set[PrimitiveTag], list[str]]`
- **fn** [[core-transformer-py-_rule_signal_for_detection]]`(tags, objective, constraints) → tuple[set[PrimitiveTag], list[str]]`
- **fn** [[core-transformer-py-_rule_temporal_binding]]`(tags, objective, constraints) → tuple[set[PrimitiveTag], list[str]]`
- **fn** [[core-transformer-py-_rule_constraint_must_include]]`(tags, objective, constraints) → tuple[set[PrimitiveTag], list[str]]`
- **fn** [[core-transformer-py-transform]]`(primitives, objective, constraints, context) → TransformationResult`
- **fn** [[core-transformer-py-_completeness_score]]`(tags) → float`
- **fn** [[core-transformer-py-_closure_score]]`(tags) → float`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from core.primitives import L0
from core.primitives import PrimitiveTag
from core.primitives import validate_composition_tags
```
