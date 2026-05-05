---
type: codebase-file
path: scripts/higgsfield_smoke_test.py
module: scripts.higgsfield_smoke_test
lines: 78
size: 2282
tags: [entry-point]
generated: 2026-04-12
---

# scripts/higgsfield_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Higgsfield Cloud API end-to-end smoke test.

Fires the cheapest possible Soul generation through the EOS wrapper,
verifies the `higgsfield_jobs` row was inserted, and polls status a
few times so we can confirm auth + submit + request_id extraction
...

**Lines:** 78 | **Size:** 2,282 bytes

## Depends On

- [[eos_ai-db-py]]
- [[eos_ai-higgsfield_client-py]]

## Contains

- **fn** [[scripts-higgsfield_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import sys
import time
from eos_ai.db import get_conn
from eos_ai.higgsfield_client import generate
from eos_ai.higgsfield_client import get_status
```
