---
type: codebase-file
path: eos_ai/substrate/backend_selection_engine.py
module: eos_ai.substrate.backend_selection_engine
lines: 165
size: 5331
generated: 2026-05-07
---

# eos_ai/substrate/backend_selection_engine.py

Backend selection engine for Phase 96.3.

Selects the best backend for a given task based on completeness,
safety, provenance, independence, and governance compatibility.

...

**Lines:** 165 | **Size:** 5,331 bytes

## Depends On

- [[eos_ai-substrate-backend_registry_contracts-py]]

## Contains

- **class** [[eos_ai-substrate-backend_selection_engine-py-SelectionTask]] — 0 methods
- **class** [[eos_ai-substrate-backend_selection_engine-py-SelectionResult]] — 1 methods
- **fn** [[eos_ai-substrate-backend_selection_engine-py-detect_when_backend_is_interface_only]]`(profile) → bool`
- **fn** [[eos_ai-substrate-backend_selection_engine-py-detect_when_backend_is_true_fallback]]`(profile) → bool`
- **fn** [[eos_ai-substrate-backend_selection_engine-py-filter_backends_by_policy]]`(task, profiles) → list[BackendProfile]`
- **fn** [[eos_ai-substrate-backend_selection_engine-py-_score_backend]]`(task, profile) → int`
- **fn** [[eos_ai-substrate-backend_selection_engine-py-rank_backends_for_task]]`(task, profiles) → list[BackendProfile]`
- **fn** [[eos_ai-substrate-backend_selection_engine-py-select_best_backend]]`(task, profiles) → SelectionResult`
- **fn** [[eos_ai-substrate-backend_selection_engine-py-explain_backend_selection]]`(selected, rejected) → str`
- **fn** [[eos_ai-substrate-backend_selection_engine-py-require_backend_parity_if_test_demands_it]]`(task) → bool`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from eos_ai.substrate.backend_registry_contracts import BackendCategory
from eos_ai.substrate.backend_registry_contracts import BackendImplementationType
from eos_ai.substrate.backend_registry_contracts import BackendProfile
from eos_ai.substrate.backend_registry_contracts import BackendSelectionFactor
from eos_ai.substrate.backend_registry_contracts import BackendStatus
```
