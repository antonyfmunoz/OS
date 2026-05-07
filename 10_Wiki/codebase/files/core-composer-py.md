---
type: codebase-file
path: core/composer.py
module: core.composer
lines: 320
size: 11880
generated: 2026-05-07
---

# core/composer.py

Composition Engine — converts intent + context into executable primitive structures.

Flow:
    intent (str)
    → resolve domain composition type (L2)
...

**Lines:** 320 | **Size:** 11,880 bytes

## Depends On

- [[core-context-py]]
- [[core-domain-creator-py]]
- [[core-domain-eos-py]]
- [[core-domain-lyfe-py]]
- [[core-primitives-py]]

## Used By

- [[core-execution_bridge-py]]
- [[core-router-py]]

## Contains

- **class** [[core-composer-py-ComposedStructure]] — 2 methods
- **fn** [[core-composer-py-resolve_domain_type]]`(intent) → str`
- **fn** [[core-composer-py-_populate_from_context]]`(composition, context) → DomainComposition`
- **fn** [[core-composer-py-compose]]`(intent, context) → ComposedStructure`
- **fn** [[core-composer-py-validate_composition]]`(structure) → list[str]`
- **fn** [[core-composer-py-trace_to_primitives]]`(structure) → list[dict[str, Any]]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from core.context import CompositionContext
from core.context import ContextualComposition
from core.context import apply_context
from core.domain.eos import DOMAIN_TYPES
from core.domain.eos import Channel
from core.domain.eos import DomainComposition
from core.domain.eos import ICP
from core.domain.eos import KPI
from core.domain.eos import Offer
from core.domain.eos import Role
from core.domain.eos import Workflow
from core.domain.lyfe import Habit
from core.domain.lyfe import Energy
from core.domain.lyfe import Focus
from core.domain.lyfe import IdentityState
from core.domain.creator import Content
from core.domain.creator import Audience
from core.domain.creator import Platform
from core.domain.creator import Engagement
from core.primitives import PrimitiveTag
from core.primitives import decompose_to_dict
from core.primitives import validate_composition_tags
```
