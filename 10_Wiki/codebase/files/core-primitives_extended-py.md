---
type: codebase-file
path: core/primitives_extended.py
module: core.primitives_extended
lines: 244
size: 8381
generated: 2026-05-07
---

# core/primitives_extended.py

Extended Primitive Attributes — derived overlays on L0 without breaking immutability.

These are NOT new primitives.  They are computed attributes that overlay
existing L0 primitives to provide richer analysis.  Every extension
maps back to one or more L0 tags and is fully optional — the system
...

**Lines:** 244 | **Size:** 8,381 bytes

## Depends On

- [[core-primitives-py]]

## Contains

- **class** [[core-primitives_extended-py-PrimitiveExtension]] — 1 methods
- **class** [[core-primitives_extended-py-ExtendedPrimitiveSet]] — 6 methods
- **fn** [[core-primitives_extended-py-compute_extensions]]`(tags, context) → ExtendedPrimitiveSet`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from core.primitives import PrimitiveTag
```
