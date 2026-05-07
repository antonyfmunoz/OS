---
type: codebase-file
path: scripts/check_stop_condition.py
module: scripts.check_stop_condition
lines: 88
size: 2217
tags: [entry-point]
generated: 2026-05-07
---

# scripts/check_stop_condition.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Stop hook handler.
Boris Cherny: exit 2 to keep Claude working.
EOS: conditional — check if current task
requires continuation before deciding.

...

**Lines:** 88 | **Size:** 2,217 bytes

## Contains

- **fn** [[scripts-check_stop_condition-py-should_continue]]`() → bool`
- **fn** [[scripts-check_stop_condition-py-main]]`()`

## Import Statements

```python
import sys
import os
import json
```
