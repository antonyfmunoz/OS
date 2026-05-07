---
type: codebase-file
path: eos_ai/transaction_workflow.py
module: eos_ai.transaction_workflow
lines: 287
size: 10158
tags: [entry-point]
generated: 2026-05-07
---

# eos_ai/transaction_workflow.py

> **ENTRY POINT** — Contains `if __name__` or server start.

TransactionWorkflow — end-to-end transaction lifecycle.

lead → client → transaction → fulfillment

Each step writes to Neon. The full cycle proves one company
...

**Lines:** 287 | **Size:** 10,158 bytes

## Depends On

- [[eos_ai-db-py]]

## Contains

- **class** [[eos_ai-transaction_workflow-py-TransactionWorkflow]] — 9 methods

## Import Statements

```python
import sys
import os
from datetime import datetime
from datetime import timezone
from eos_ai.db import get_conn
```
