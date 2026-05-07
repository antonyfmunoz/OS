---
type: codebase-file
path: eos_ai/execution_spine.py
module: eos_ai.execution_spine
lines: 171
size: 6029
tags: [entry-point]
generated: 2026-05-07
---

# eos_ai/execution_spine.py

> **ENTRY POINT** — Contains `if __name__` or server start.

ExecutionSpine — single execution path for all EOS operations.

Every LLM call in the system should flow through here:
    spine = ExecutionSpine()
    response = spine.run(message, unified_context, ...)
...

**Lines:** 171 | **Size:** 6,029 bytes

## Contains

- **class** [[eos_ai-execution_spine-py-ExecutionSpine]] — 1 methods

## Import Statements

```python
import os
import sys
import threading
import uuid
from datetime import datetime
from datetime import timezone
```
