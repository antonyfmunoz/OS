---
type: codebase-file
path: core/domain/eos.py
module: core.domain.eos
lines: 273
size: 8758
generated: 2026-05-07
---

# core/domain/eos.py

EOS domain compositions — L2 business structures mapped to L0 primitives.

Every structure here decomposes into ontological primitives via
`to_primitives()`.  These are the canonical building blocks of the
EOS business domain.  Other domains (LyfeOS, CreatorOS) will follow
...

**Lines:** 273 | **Size:** 8,758 bytes

## Depends On

- [[core-primitives-py]]

## Used By

- [[core-composer-py]]
- [[core-context-py]]
- [[core-domain-creator-py]]
- [[core-domain-lyfe-py]]

## Contains

- **class** [[core-domain-eos-py-DomainComposition]] — 4 methods
- **class** [[core-domain-eos-py-ICP]] — 1 methods
- **class** [[core-domain-eos-py-Offer]] — 1 methods
- **class** [[core-domain-eos-py-Channel]] — 1 methods
- **class** [[core-domain-eos-py-Workflow]] — 1 methods
- **class** [[core-domain-eos-py-KPI]] — 1 methods
- **class** [[core-domain-eos-py-Role]] — 1 methods
- **fn** [[core-domain-eos-py-_register_cross_domain]]`() → None`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from core.primitives import PrimitiveTag
from core.primitives import decompose_to_dict
from core.primitives import validate_composition_tags
```
