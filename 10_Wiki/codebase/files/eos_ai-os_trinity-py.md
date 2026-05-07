---
type: codebase-file
path: eos_ai/os_trinity.py
module: eos_ai.os_trinity
lines: 519
size: 21448
generated: 2026-05-07
---

# eos_ai/os_trinity.py

OSTrinity — OS Trinity harness layer.

Manages three cross-product concerns:
  1. cross_product_permissions  — user-granted data sharing between products
  2. user_intelligence_profiles — harness-level user profile (survives product boundaries)
...

**Lines:** 519 | **Size:** 21,448 bytes

## Depends On

- [[eos_ai-context-py]]

## Contains

- **class** [[eos_ai-os_trinity-py-OSTrinity]] — 11 methods

## Import Statements

```python
import json
import uuid
from datetime import datetime
from datetime import timezone
from eos_ai.context import EOSContext
```
