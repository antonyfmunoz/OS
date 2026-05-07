---
type: codebase-file
path: eos_ai/substrate/ritual_reconciler.py
module: eos_ai.substrate.ritual_reconciler
lines: 175
size: 6266
generated: 2026-05-07
---

# eos_ai/substrate/ritual_reconciler.py

Ritual reconciler — bounded visibility of station action outcomes in rituals.

`ritual.outputs["body_actions"]` already carries `action_id` for every
station action a ritual body proposed (see ritual_body.py). This module
adds the smallest useful consumer for that metadata: a reconcile pass that
...

**Lines:** 175 | **Size:** 6,266 bytes

## Depends On

- [[eos_ai-substrate-result_store-py]]
- [[eos_ai-substrate-rituals-py]]

## Used By

- [[scripts-substrate_drain_station-py]]
- [[scripts-substrate_durable_result_smoke_test-py]]
- [[scripts-substrate_result_loop_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-ritual_reconciler-py-ReconcileSummary]] — 3 methods
- **fn** [[eos_ai-substrate-ritual_reconciler-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-ritual_reconciler-py-reconcile_ritual]]`(ritual_id) → Optional[ReconcileSummary]`
- **fn** [[eos_ai-substrate-ritual_reconciler-py-reconcile_recent]]`(limit) → list[ReconcileSummary]`

## Import Statements

```python
from __future__ import annotations
import sys
from dataclasses import dataclass
from dataclasses import asdict
from dataclasses import field
from typing import Optional
from eos_ai.substrate.result_store import ResultStore
from eos_ai.substrate.result_store import get_result_store
from eos_ai.substrate.rituals import RitualRegistry
```
