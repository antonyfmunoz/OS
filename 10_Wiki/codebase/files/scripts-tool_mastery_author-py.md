---
type: codebase-file
path: scripts/tool_mastery_author.py
module: scripts.tool_mastery_author
lines: 125
size: 3817
tags: [entry-point]
generated: 2026-04-12
---

# scripts/tool_mastery_author.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Tool Mastery author dispatcher.

Thin shim that runs the Tool Mastery Author Agent against a research
artifact. This script is the target of `tool_mastery.author` actions
queued by the Research Agent through the Control Plane.
...

**Lines:** 125 | **Size:** 3,817 bytes

## Depends On

- [[core-tool_mastery_author_agent-agent-py]]
- [[core-tool_mastery_author_agent-models-py]]

## Contains

- **fn** [[scripts-tool_mastery_author-py-_run]]`(tool, artifact) → int`
- **fn** [[scripts-tool_mastery_author-py-_consume_action]]`(path) → int`
- **fn** [[scripts-tool_mastery_author-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from core.tool_mastery_author_agent.agent import author
from core.tool_mastery_author_agent.models import AuthorRequest
from core.tool_mastery_author_agent.models import AuthorStatus
```
