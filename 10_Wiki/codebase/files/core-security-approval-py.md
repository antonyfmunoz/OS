---
type: codebase-file
path: core/security/approval.py
module: core.security.approval
lines: 415
size: 15083
generated: 2026-04-12
---

# core/security/approval.py

approval.py — Approval queue for high-risk actions.

Flow (matches the objective in the spec):

    ActionSystem.execute()
...

**Lines:** 415 | **Size:** 15,083 bytes

## Used By

- [[core-security-cli-py]]
- [[scripts-security_smoke_test-py]]

## Contains

- **class** [[core-security-approval-py-ApprovalStatus]] — 0 methods
- **class** [[core-security-approval-py-ApprovalAction]] — 0 methods
- **class** [[core-security-approval-py-ApprovalRequest]] — 2 methods
- **class** [[core-security-approval-py-ApprovalError]] — 0 methods
- **class** [[core-security-approval-py-ApprovalQueue]] — 15 methods
- **fn** [[core-security-approval-py-_new_id]]`() → str`

## Import Statements

```python
from __future__ import annotations
import json
import time
import uuid
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from pathlib import Path
from typing import Iterable
```
