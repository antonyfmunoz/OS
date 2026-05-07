---
type: codebase-file
path: scripts/eos_os_smoke_test.py
module: scripts.eos_os_smoke_test
lines: 251
size: 8492
tags: [entry-point]
generated: 2026-05-07
---

# scripts/eos_os_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

eos_os_smoke_test.py — End-to-end verification for the EOS AI OS.

Exercises every layer of the unified stack without relying on external
LLM providers. Prints a PASS/FAIL line per check and exits non-zero on
the first failure so CI / ops can trust the return code.
...

**Lines:** 251 | **Size:** 8,492 bytes

## Contains

- **class** [[scripts-eos_os_smoke_test-py-SmokeRunner]] — 3 methods
- **fn** [[scripts-eos_os_smoke_test-py-check_imports]]`() → None`
- **fn** [[scripts-eos_os_smoke_test-py-check_capability]]`() → None`
- **fn** [[scripts-eos_os_smoke_test-py-check_harness]]`() → None`
- **fn** [[scripts-eos_os_smoke_test-py-check_persistent_agents]]`() → None`
- **fn** [[scripts-eos_os_smoke_test-py-check_optimizer]]`() → None`
- **fn** [[scripts-eos_os_smoke_test-py-check_observability]]`() → None`
- **fn** [[scripts-eos_os_smoke_test-py-check_control_plane_once]]`() → None`
- **fn** [[scripts-eos_os_smoke_test-py-check_data_files]]`() → None`
- **fn** [[scripts-eos_os_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import json
import subprocess
import sys
import time
import traceback
from pathlib import Path
```
