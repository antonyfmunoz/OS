---
type: codebase-file
path: core/action_system/tme.py
module: core.action_system.tme
lines: 78
size: 3064
generated: 2026-04-12
---

# core/action_system/tme.py

Tool Mastery Engine / Manager integration for the Control Plane.

Two concerns live here:

    1. Advisory skill search (legacy) — `query_relevant_skills` shells
...

**Lines:** 78 | **Size:** 3,064 bytes

## Contains

- **fn** [[core-action_system-tme-py-query_relevant_skills]]`(term) → dict`
- **fn** [[core-action_system-tme-py-ensure_tool_mastery]]`(tool) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import subprocess
from typing import Any
```
