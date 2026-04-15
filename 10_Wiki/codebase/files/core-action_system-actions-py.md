---
type: codebase-file
path: core/action_system/actions.py
module: core.action_system.actions
lines: 84
size: 2636
generated: 2026-04-12
---

# core/action_system/actions.py

Action object — the canonical unit of control in EOS.

Every meaningful thing an agent wants to do is wrapped as an Action and
passed through the Control Plane (propose → validate → approve → execute → log).

**Lines:** 84 | **Size:** 2,636 bytes

## Used By

- [[scripts-deferred-py]]

## Contains

- **class** [[core-action_system-actions-py-Action]] — 1 methods
- **fn** [[core-action_system-actions-py-propose_action]]`(type, description) → Action`

## Import Statements

```python
from __future__ import annotations
import uuid
from dataclasses import dataclass
from dataclasses import field
from dataclasses import asdict
from datetime import datetime
from datetime import timezone
from typing import Any
```
