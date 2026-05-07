---
type: codebase-file
path: core/primitives.py
module: core.primitives
lines: 251
size: 9064
generated: 2026-05-07
---

# core/primitives.py

L0 Ontological Primitives — the immutable atoms of EOS.

Every domain concept in EOS decomposes into combinations of these 10
universal primitives.  They are ontological — they describe *what exists*
in any system that acts on the world — and they never change.
...

**Lines:** 251 | **Size:** 9,064 bytes

## Used By

- [[core-composer-py]]
- [[core-context-py]]
- [[core-domain-creator-py]]
- [[core-domain-eos-py]]
- [[core-domain-lyfe-py]]
- [[core-feedback-py]]
- [[core-matcher-py]]
- [[core-memory_evolution-py]]
- [[core-primitives_extended-py]]
- [[core-reality_input-py]]
- [[core-router-py]]
- [[core-self_improvement-py]]
- [[core-transformer-py]]

## Contains

- **class** [[core-primitives-py-PrimitiveTag]] — 0 methods
- **class** [[core-primitives-py-OntologicalPrimitive]] — 0 methods
- **fn** [[core-primitives-py-validate_primitive_set]]`(tags) → list[str]`
- **fn** [[core-primitives-py-validate_composition_tags]]`(tags) → list[str]`
- **fn** [[core-primitives-py-decompose_to_dict]]`(tags) → list[dict[str, Any]]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from enum import unique
from typing import Any
```
