---
type: codebase-file
path: scripts/decisions.py
module: scripts.decisions
lines: 202
size: 6868
tags: [entry-point]
generated: 2026-05-07
---

# scripts/decisions.py

> **ENTRY POINT** — Contains `if __name__` or server start.

decisions.py — operator CLI for the Control Plane decision log.

Reads `logs/decisions/YYYY-MM-DD-decisions.jsonl` files append-only.
This tool is READ-ONLY and imports nothing from `core.action_system` —
if the Control Plane is broken, this tool still works. Matching the
...

**Lines:** 202 | **Size:** 6,868 bytes

## Contains

- **fn** [[scripts-decisions-py-_iter_log_files]]`(since) → list[str]`
- **fn** [[scripts-decisions-py-_iter_records]]`(paths) → Iterable[dict[str, Any]]`
- **fn** [[scripts-decisions-py-_short]]`(s, n) → str`
- **fn** [[scripts-decisions-py-_truncate]]`(s, n) → str`
- **fn** [[scripts-decisions-py-cmd_list]]`(args) → int`
- **fn** [[scripts-decisions-py-cmd_show]]`(args) → int`
- **fn** [[scripts-decisions-py-cmd_for_action]]`(args) → int`
- **fn** [[scripts-decisions-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import json
import os
import sys
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
from typing import Iterable
```
