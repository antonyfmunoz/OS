---
type: codebase-file
path: eos_ai/substrate/target_policy.py
module: eos_ai.substrate.target_policy
lines: 214
size: 7111
generated: 2026-05-07
---

# eos_ai/substrate/target_policy.py

Hybrid Execution Target Policy v1 — deterministic target resolution.

Purpose
-------
Resolves which execution target (``"local"`` or ``"vps"``) a request should
...

**Lines:** 214 | **Size:** 7,111 bytes

## Contains

- **fn** [[eos_ai-substrate-target_policy-py-_flag_truthy]]`(env_name) → bool`
- **fn** [[eos_ai-substrate-target_policy-py-_clamp_target]]`(raw, default) → str`
- **fn** [[eos_ai-substrate-target_policy-py-_mode_default]]`(mode) → str`
- **fn** [[eos_ai-substrate-target_policy-py-resolve_execution_target]]`(mode, metadata) → str`
- **fn** [[eos_ai-substrate-target_policy-py-resolve_execution_policy]]`(mode, metadata) → dict[str, Any]`
- **fn** [[eos_ai-substrate-target_policy-py-should_delegate_product_to_local]]`(text, metadata) → bool`
- **fn** [[eos_ai-substrate-target_policy-py-_check_delegation]]`(metadata, text) → tuple[bool, Optional[str]]`

## Import Statements

```python
from __future__ import annotations
import os
from typing import Any
from typing import Optional
```
