---
type: codebase-class
file: core/primitives_extended.py
line: 60
generated: 2026-05-07
---

# ExtendedPrimitiveSet

**File:** [[core-primitives_extended-py]] | **Line:** 60

A set of L0 primitives with optional computed extensions.

The base primitive set is unchanged.  Extensions ride alongside
and can be queried by downstream consumers that understand them.
Consumers that don't understand extensions see a normal primitive set.

## Methods

- [[core-primitives_extended-py-ExtendedPrimitiveSet-polarity]]`() → str | None` — Direction of movement: 'positive', 'negative', or 'neutral'.
- [[core-primitives_extended-py-ExtendedPrimitiveSet-intensity]]`() → float | None` — Magnitude of signal/change (0.0-1.0).
- [[core-primitives_extended-py-ExtendedPrimitiveSet-rhythm]]`() → str | None` — Temporal pattern: 'accelerating', 'decelerating', 'steady', 'irregular'.
- [[core-primitives_extended-py-ExtendedPrimitiveSet-emergence]]`() → bool` — Whether an unexpected outcome was detected.
- [[core-primitives_extended-py-ExtendedPrimitiveSet-leverage]]`() → float | None` — Output/input ratio — how much result per unit effort.
- [[core-primitives_extended-py-ExtendedPrimitiveSet-to_dict]]`() → dict[str, Any]` — 

## Decorators

- `@dataclass`
