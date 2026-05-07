---
type: codebase-file
path: core/context.py
module: core.context
lines: 125
size: 4192
generated: 2026-05-07
---

# core/context.py

L1 Context Layer — customisation inputs that shape compositions.

Context captures intent, preferences, identity, and client-specific
data.  It affects HOW domain compositions (L2) are populated but
NEVER modifies L0 primitives.
...

**Lines:** 125 | **Size:** 4,192 bytes

## Depends On

- [[core-domain-eos-py]]
- [[core-primitives-py]]

## Used By

- [[core-composer-py]]

## Contains

- **class** [[core-context-py-CompositionContext]] — 1 methods
- **class** [[core-context-py-ContextualComposition]] — 4 methods
- **fn** [[core-context-py-apply_context]]`(composition, context) → ContextualComposition`

## Import Statements

```python
from __future__ import annotations
import copy
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from core.domain.eos import DomainComposition
from core.primitives import PrimitiveTag
```
