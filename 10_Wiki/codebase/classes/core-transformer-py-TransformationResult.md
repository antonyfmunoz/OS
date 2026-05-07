---
type: codebase-class
file: core/transformer.py
line: 35
generated: 2026-05-07
---

# TransformationResult

**File:** [[core-transformer-py]] | **Line:** 35

Immutable record of a transformation decision.

Everything is traceable: original input, what changed, why, and
the expected impact.

## Methods

- [[core-transformer-py-TransformationResult-changed]]`() → bool` — 
- [[core-transformer-py-TransformationResult-added]]`() → frozenset[PrimitiveTag]` — 
- [[core-transformer-py-TransformationResult-removed]]`() → frozenset[PrimitiveTag]` — 
- [[core-transformer-py-TransformationResult-to_dict]]`() → dict[str, Any]` — 

## Decorators

- `@dataclass`
