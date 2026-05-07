---
type: codebase-file
path: core/mastery_engine/mastery_requirement_contracts.py
module: core.mastery_engine.mastery_requirement_contracts
lines: 114
size: 3947
generated: 2026-05-07
---

# core/mastery_engine/mastery_requirement_contracts.py

Mastery requirement contracts for the Universal Mastery Layer.

Each mastery requirement defines scoped, versioned, testable, proof-
backed competence that UMH must possess before execution.

...

**Lines:** 114 | **Size:** 3,947 bytes

## Contains

- **class** [[core-mastery_engine-mastery_requirement_contracts-py-MasteryRequirement]] — 1 methods
- **fn** [[core-mastery_engine-mastery_requirement_contracts-py-build_mastery_requirement]]`(mastery_id, category, target, capability_scope, risk_level, required_freshness, required_tests, required_proof, current_status, gaps) → MasteryRequirement`
- **fn** [[core-mastery_engine-mastery_requirement_contracts-py-mastery_requirement_is_satisfied]]`(requirement) → bool`
- **fn** [[core-mastery_engine-mastery_requirement_contracts-py-mastery_requirement_is_stale]]`(requirement) → bool`
- **fn** [[core-mastery_engine-mastery_requirement_contracts-py-mastery_requirement_blocks_execution]]`(requirement) → bool`
- **fn** [[core-mastery_engine-mastery_requirement_contracts-py-summarize_mastery_requirement]]`(requirement) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from universal_mastery import MasteryCategory
from universal_mastery import MasteryStatus
```
