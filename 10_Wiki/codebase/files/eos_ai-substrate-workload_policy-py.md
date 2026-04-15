---
type: codebase-file
path: eos_ai/substrate/workload_policy.py
module: eos_ai.substrate.workload_policy
lines: 193
size: 5974
generated: 2026-04-12
---

# eos_ai/substrate/workload_policy.py

Workload Classification Policy v1 — deterministic execution weight.

Purpose
-------
Classifies incoming requests by execution weight — lightweight, standard,
...

**Lines:** 193 | **Size:** 5,974 bytes

## Used By

- [[eos_ai-substrate-discord_text_transport-py]]

## Contains

- **fn** [[eos_ai-substrate-workload_policy-py-classify_workload]]`(text, mode, workflow_kind, metadata) → dict[str, Any]`
- **fn** [[eos_ai-substrate-workload_policy-py-workload_weight_order]]`(wc) → int`
- **fn** [[eos_ai-substrate-workload_policy-py-_result]]`(workload_class, reason, matched_rule) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from typing import Any
from typing import Optional
```
