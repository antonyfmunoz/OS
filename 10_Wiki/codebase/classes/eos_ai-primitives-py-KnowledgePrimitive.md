---
type: codebase-class
file: eos_ai/primitives.py
line: 42
generated: 2026-04-12
---

# KnowledgePrimitive

**File:** [[eos_ai-primitives-py]] | **Line:** 42

A single business principle with full validity conditions.

stage_applicability maps stage int to bool:
    {1: False, 2: True, 3: True}
A stage 1 founder should NOT receive advice marked False at stage 1.
...

## Decorators

- `@dataclass`
