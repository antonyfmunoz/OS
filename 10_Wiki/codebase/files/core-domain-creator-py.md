---
type: codebase-file
path: core/domain/creator.py
module: core.domain.creator
lines: 145
size: 4920
generated: 2026-05-07
---

# core/domain/creator.py

CreatorOS domain compositions — content creation structures.

Maps content-creation concepts to L0 primitives following the same
pattern as EOS business compositions.

...

**Lines:** 145 | **Size:** 4,920 bytes

## Depends On

- [[core-domain-eos-py]]
- [[core-primitives-py]]

## Used By

- [[core-composer-py]]

## Contains

- **class** [[core-domain-creator-py-Content]] — 1 methods
- **class** [[core-domain-creator-py-Audience]] — 1 methods
- **class** [[core-domain-creator-py-Platform]] — 1 methods
- **class** [[core-domain-creator-py-Engagement]] — 1 methods

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from core.domain.eos import DomainComposition
from core.primitives import PrimitiveTag
```
