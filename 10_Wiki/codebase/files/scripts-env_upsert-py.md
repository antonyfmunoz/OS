---
type: codebase-file
path: scripts/env_upsert.py
module: scripts.env_upsert
lines: 105
size: 3192
tags: [entry-point]
generated: 2026-05-07
---

# scripts/env_upsert.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Idempotent .env key upsert.

Usage:
    env_upsert.py <path> KEY=VALUE [KEY=VALUE ...]

...

**Lines:** 105 | **Size:** 3,192 bytes

## Contains

- **fn** [[scripts-env_upsert-py-_parse_args]]`(argv) → tuple[Path, list[tuple[str, str]]]`
- **fn** [[scripts-env_upsert-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import os
import re
import sys
from pathlib import Path
```
