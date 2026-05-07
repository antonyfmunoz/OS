---
type: codebase-file
path: core/tool_mastery_research_agent/paths.py
module: core.tool_mastery_research_agent.paths
lines: 23
size: 737
generated: 2026-05-07
---

# core/tool_mastery_research_agent/paths.py

Path resolution for the Tool Mastery Research Agent.

Centralised so portability work can replace hardcoded /opt/OS with an
EOS_ROOT env var in exactly one place. Mirrors the Manager's paths.py
pattern.

**Lines:** 23 | **Size:** 737 bytes

## Import Statements

```python
from __future__ import annotations
import os
from pathlib import Path
```
