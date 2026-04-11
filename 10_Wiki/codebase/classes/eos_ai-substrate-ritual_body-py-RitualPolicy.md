---
type: codebase-class
file: eos_ai/substrate/ritual_body.py
line: 61
generated: 2026-04-11
---

# RitualPolicy

**File:** [[eos_ai-substrate-ritual_body-py]] | **Line:** 61

Declarative body for a ritual.

Every field is optional. A policy with nothing set produces a no-op body
(ritual stays a pure lifecycle marker). Setting a field opts into one
specific safe action.
...

## Decorators

- `@dataclass`
