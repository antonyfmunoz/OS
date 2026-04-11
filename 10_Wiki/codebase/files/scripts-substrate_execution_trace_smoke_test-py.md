---
type: codebase-file
path: scripts/substrate_execution_trace_smoke_test.py
module: scripts.substrate_execution_trace_smoke_test
lines: 449
size: 19010
tags: [entry-point]
generated: 2026-04-11
---

# scripts/substrate_execution_trace_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Smoke test for Execution Trace Layer v1.

Validates:
  1-14: trace object, history, thread-local, scenarios
  15-18: architectural tripwires (one router, no daemon, clean imports, no leak)

**Lines:** 449 | **Size:** 19,010 bytes

## Contains

- **fn** [[scripts-substrate_execution_trace_smoke_test-py-check]]`(name, cond, detail) → None`
- **fn** [[scripts-substrate_execution_trace_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_execution_trace_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import importlib
import os
import sys
```
