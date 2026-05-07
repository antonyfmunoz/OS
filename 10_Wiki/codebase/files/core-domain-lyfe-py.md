---
type: codebase-file
path: core/domain/lyfe.py
module: core.domain.lyfe
lines: 148
size: 5031
generated: 2026-05-07
---

# core/domain/lyfe.py

LyfeOS domain compositions — personal operating system structures.

Maps life-optimization concepts to L0 primitives following the same
pattern as EOS business compositions.

...

**Lines:** 148 | **Size:** 5,031 bytes

## Depends On

- [[core-domain-eos-py]]
- [[core-primitives-py]]

## Used By

- [[core-composer-py]]

## Contains

- **class** [[core-domain-lyfe-py-Habit]] — 1 methods
- **class** [[core-domain-lyfe-py-Energy]] — 1 methods
- **class** [[core-domain-lyfe-py-Focus]] — 1 methods
- **class** [[core-domain-lyfe-py-IdentityState]] — 1 methods

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from core.domain.eos import DomainComposition
from core.primitives import PrimitiveTag
```
