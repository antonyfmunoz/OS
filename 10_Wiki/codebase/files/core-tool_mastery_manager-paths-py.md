---
type: codebase-file
path: core/tool_mastery_manager/paths.py
module: core.tool_mastery_manager.paths
lines: 26
size: 934
generated: 2026-04-12
---

# core/tool_mastery_manager/paths.py

Path resolution for the Tool Mastery Manager.

Centralised so portability work can replace hardcoded /opt/OS with an
EOS_ROOT env var in exactly one place. Everything in the manager imports
paths from here rather than hardcoding.

**Lines:** 26 | **Size:** 934 bytes

## Used By

- [[scripts-tool_mastery_research_dispatcher-py]]

## Import Statements

```python
from __future__ import annotations
import os
from pathlib import Path
```
