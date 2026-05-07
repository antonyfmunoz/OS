---
type: codebase-class
file: core/objective_engine.py
line: 33
generated: 2026-05-07
---

# ObjectiveFunction

**File:** [[core-objective_engine-py]] | **Line:** 33

One objective in a multi-objective set.

Args:
    name:            Human-readable identifier.
    metric_name:     Key to look up in real_data dict.
...

## Methods

- [[core-objective_engine-py-ObjectiveFunction-score]]`(value) → float` — Score a single metric value against this objective.
- [[core-objective_engine-py-ObjectiveFunction-achieved]]`(value) → bool` — Check if the threshold is met.
- [[core-objective_engine-py-ObjectiveFunction-to_dict]]`() → dict[str, Any]` — 

## Decorators

- `@dataclass`
