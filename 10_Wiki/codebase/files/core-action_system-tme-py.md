---
type: codebase-file
path: core/action_system/tme.py
module: core.action_system.tme
lines: 137
size: 5005
generated: 2026-05-07
---

# core/action_system/tme.py

Tool Mastery Engine / Manager integration for the Control Plane.

Two concerns live here:

    1. Advisory skill search (legacy) — `query_relevant_skills` shells
...

**Lines:** 137 | **Size:** 5,005 bytes

## Contains

- **fn** [[core-action_system-tme-py-query_relevant_skills]]`(term) → dict`
- **fn** [[core-action_system-tme-py-ensure_tool_mastery]]`(tool) → dict[str, Any]`
- **fn** [[core-action_system-tme-py-ensure_mastery_before_tool_execution]]`(tool_name) → dict[str, Any]`
- **fn** [[core-action_system-tme-py-resolve_mastery_for_user_intent]]`(text) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import subprocess
from typing import Any
```
