---
type: codebase-file
path: eos_ai/platforms/eos/context_builder.py
module: eos_ai.platforms.eos.context_builder
lines: 371
size: 12771
generated: 2026-05-07
---

# eos_ai/platforms/eos/context_builder.py

Context builder — assembles structured context dicts from substrate state.

Every context function returns a dict with four stable sections:

    {
...

**Lines:** 371 | **Size:** 12,771 bytes

## Depends On

- [[eos_ai-platforms-eos-roles-py]]

## Used By

- [[eos_ai-platforms-eos-ea_orchestrator-py]]

## Contains

- **fn** [[eos_ai-platforms-eos-context_builder-py-_log]]`(msg) → None`
- **fn** [[eos_ai-platforms-eos-context_builder-py-_utcnow]]`() → str`
- **fn** [[eos_ai-platforms-eos-context_builder-py-_safe]]`(fn, default)`
- **fn** [[eos_ai-platforms-eos-context_builder-py-_get_operator_session]]`()`
- **fn** [[eos_ai-platforms-eos-context_builder-py-_get_task_summary]]`() → dict`
- **fn** [[eos_ai-platforms-eos-context_builder-py-_get_pipeline_summary]]`() → dict`
- **fn** [[eos_ai-platforms-eos-context_builder-py-_get_perception_summary]]`() → dict`
- **fn** [[eos_ai-platforms-eos-context_builder-py-_get_station_summary]]`() → dict`
- **fn** [[eos_ai-platforms-eos-context_builder-py-_get_live_session_summary]]`() → dict`
- **fn** [[eos_ai-platforms-eos-context_builder-py-build_ea_context]]`() → dict[str, Any]`
- **fn** [[eos_ai-platforms-eos-context_builder-py-build_ceo_context]]`() → dict[str, Any]`
- **fn** [[eos_ai-platforms-eos-context_builder-py-build_portfolio_context]]`() → dict[str, Any]`
- **fn** [[eos_ai-platforms-eos-context_builder-py-build_context_for_role]]`(role) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import sys
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Optional
from eos_ai.platforms.eos.roles import EOSRole
```
