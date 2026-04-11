---
type: codebase-file
path: scripts/tool_mastery_research_dispatcher.py
module: scripts.tool_mastery_research_dispatcher
lines: 311
size: 11030
tags: [entry-point]
generated: 2026-04-11
---

# scripts/tool_mastery_research_dispatcher.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Tool Mastery research dispatcher.

This is the target of Control Plane actions queued by the Tool Mastery
Manager. When the Manager decides a tool needs `research`, `refresh`,
or `repair` work, it enqueues a `run_script` action pointing at this
...

**Lines:** 311 | **Size:** 11,030 bytes

## Depends On

- [[core-tool_mastery_manager-coverage-py]]
- [[core-tool_mastery_manager-paths-py]]

## Contains

- **fn** [[scripts-tool_mastery_research_dispatcher-py-_plan_research]]`(slug) → dict`
- **fn** [[scripts-tool_mastery_research_dispatcher-py-_plan_refresh]]`(slug, report) → dict`
- **fn** [[scripts-tool_mastery_research_dispatcher-py-_plan_repair]]`(slug, report) → dict`
- **fn** [[scripts-tool_mastery_research_dispatcher-py-_drain_author_queue]]`() → int`
- **fn** [[scripts-tool_mastery_research_dispatcher-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from core.tool_mastery_manager.coverage import evaluate_coverage
from core.tool_mastery_manager.paths import SKILLS_TOOLS_DIR
```
