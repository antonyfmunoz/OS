---
type: codebase-file
path: scripts/test_execution_contract.py
module: scripts.test_execution_contract
lines: 112
size: 4122
tags: [entry-point]
generated: 2026-05-07
---

# scripts/test_execution_contract.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Test execution_contract.run_task() with two messages.

Verifies:
1. Both calls return ok=True with valid return shape
2. Both messages appear in Neon messages table
...

**Lines:** 112 | **Size:** 4,122 bytes

## Depends On

- [[core-execution_contract-py]]
- [[eos_ai-db-py]]
- [[eos_ai-substrate-execution_trace-py]]

## Contains

- **fn** [[scripts-test_execution_contract-py-main]]`() → None`
- **fn** [[scripts-test_execution_contract-py-_print_result]]`(label, r) → None`

## Import Statements

```python
import sys
from core.execution_contract import run_task
from eos_ai.db import get_conn
from eos_ai.db import ORG_ID
from eos_ai.substrate.execution_trace import get_trace_history
```
