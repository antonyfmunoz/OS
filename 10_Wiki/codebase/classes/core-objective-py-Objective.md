---
type: codebase-class
file: core/objective.py
line: 34
generated: 2026-05-07
---

# Objective

**File:** [[core-objective-py]] | **Line:** 34

A real-world success criterion that overrides internal pipeline scoring.

The success_metric callable receives:
    (pipeline_result: PipelineResult, real_data: dict) -> float

...

## Methods

- [[core-objective-py-Objective-evaluate]]`(result, real_data) → float` — Run the success metric against real data.

## Decorators

- `@dataclass`
