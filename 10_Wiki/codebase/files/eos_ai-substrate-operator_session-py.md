---
type: codebase-file
path: eos_ai/substrate/operator_session.py
module: eos_ai.substrate.operator_session
lines: 300
size: 12657
generated: 2026-05-07
---

# eos_ai/substrate/operator_session.py

Operator session spine — single authoritative source of truth for the
operator's daily lifecycle state.

Purpose
-------
...

**Lines:** 300 | **Size:** 12,657 bytes

## Used By

- [[eos_ai-substrate-day_workflows-py]]

## Contains

- **class** [[eos_ai-substrate-operator_session-py-OperatorDayMode]] — 0 methods
- **class** [[eos_ai-substrate-operator_session-py-OperatorSession]] — 3 methods
- **class** [[eos_ai-substrate-operator_session-py-OperatorSessionStore]] — 7 methods
- **fn** [[eos_ai-substrate-operator_session-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-operator_session-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-operator_session-py-_new_id]]`(prefix) → str`

## Import Statements

```python
from __future__ import annotations
import sys
import threading
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Optional
```
