---
type: codebase-file
path: core/matcher.py
module: core.matcher
lines: 331
size: 11583
generated: 2026-05-07
---

# core/matcher.py

Capability Matcher — selects the best execution resource for a composition.

Given a set of primitives, an objective, and constraints, the matcher
scores every registered capability and returns a ranked selection.
Scoring is a weighted combination of:
...

**Lines:** 331 | **Size:** 11,583 bytes

## Depends On

- [[core-capabilities-py]]
- [[core-primitives-py]]

## Used By

- [[core-router-py]]

## Contains

- **class** [[core-matcher-py-CapabilityScore]] — 1 methods
- **class** [[core-matcher-py-CapabilitySelection]] — 1 methods
- **fn** [[core-matcher-py-_derive_required_tasks]]`(primitives, objective) → set[str]`
- **fn** [[core-matcher-py-_task_fit_score]]`(cap, required_tasks) → float`
- **fn** [[core-matcher-py-_constraint_fit_score]]`(cap, constraints) → float`
- **fn** [[core-matcher-py-_to_threshold]]`(value) → float`
- **fn** [[core-matcher-py-match_capability]]`(primitives, objective, constraints) → CapabilitySelection`
- **fn** [[core-matcher-py-match_for_step]]`(step_description, primitives, constraints) → CapabilitySelection`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from core.capabilities import Capability
from core.capabilities import list_capabilities
from core.primitives import PrimitiveTag
```
