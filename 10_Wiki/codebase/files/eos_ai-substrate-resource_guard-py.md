---
type: codebase-file
path: eos_ai/substrate/resource_guard.py
module: eos_ai.substrate.resource_guard
lines: 273
size: 8099
generated: 2026-04-12
---

# eos_ai/substrate/resource_guard.py

Resource Guard v1 — pre-execution VPS resource check.

Purpose
-------
Prevents VPS overload by checking system resources before execution.
...

**Lines:** 273 | **Size:** 8,099 bytes

## Used By

- [[eos_ai-substrate-discord_text_transport-py]]

## Contains

- **fn** [[eos_ai-substrate-resource_guard-py-_flag_truthy]]`(env_name) → bool`
- **fn** [[eos_ai-substrate-resource_guard-py-_env_float]]`(env_name, default) → float`
- **fn** [[eos_ai-substrate-resource_guard-py-_parse_meminfo]]`() → dict[str, float]`
- **fn** [[eos_ai-substrate-resource_guard-py-_count_processes]]`() → int | None`
- **fn** [[eos_ai-substrate-resource_guard-py-current_resource_snapshot]]`() → dict[str, Any]`
- **fn** [[eos_ai-substrate-resource_guard-py-evaluate_resource_guard]]`(mode, target, workload_class, snapshot) → dict[str, Any]`
- **fn** [[eos_ai-substrate-resource_guard-py-_guard_result]]`() → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import os
from datetime import datetime
from datetime import timezone
from typing import Any
```
