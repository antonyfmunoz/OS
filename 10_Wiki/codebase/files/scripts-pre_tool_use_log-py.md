---
type: codebase-file
path: scripts/pre_tool_use_log.py
module: scripts.pre_tool_use_log
lines: 55
size: 1259
tags: [entry-point]
generated: 2026-04-12
---

# scripts/pre_tool_use_log.py

> **ENTRY POINT** — Contains `if __name__` or server start.

PreToolUse hook.
Logs every tool call before execution.
Boris Cherny: "Log every bash command
the model runs (PreToolUse)"

...

**Lines:** 55 | **Size:** 1,259 bytes

## Contains

- **fn** [[scripts-pre_tool_use_log-py-main]]`()`

## Import Statements

```python
import sys
import os
import json
import time
```
