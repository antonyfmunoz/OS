---
type: codebase-file
path: core/mastery_engine/universal_mastery.py
module: core.mastery_engine.universal_mastery
lines: 126
size: 3991
generated: 2026-05-07
---

# core/mastery_engine/universal_mastery.py

Universal Mastery / Competence Layer.

Tool Mastery Engine (TME) is the first implementation slice of a larger
Universal Mastery / Competence Layer. UMH must not execute merely
because it has access to a tool, model, environment, data source,
...

**Lines:** 126 | **Size:** 3,991 bytes

## Contains

- **class** [[core-mastery_engine-universal_mastery-py-MasteryCategory]] — 0 methods
- **class** [[core-mastery_engine-universal_mastery-py-MasteryStatus]] — 0 methods
- **class** [[core-mastery_engine-universal_mastery-py-UniversalMasteryDecision]] — 1 methods
- **fn** [[core-mastery_engine-universal_mastery-py-build_universal_mastery_decision]]`(action_id, required_categories, satisfied_categories, missing_categories, stale_categories, proof_required) → UniversalMasteryDecision`
- **fn** [[core-mastery_engine-universal_mastery-py-mastery_category_required_for_execution]]`(category) → bool`
- **fn** [[core-mastery_engine-universal_mastery-py-mastery_decision_blocks_execution]]`(decision) → bool`
- **fn** [[core-mastery_engine-universal_mastery-py-summarize_universal_mastery_decision]]`(decision) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
