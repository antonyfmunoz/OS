---
type: codebase-file
path: core/security/audit.py
module: core.security.audit
lines: 272
size: 9632
generated: 2026-05-07
---

# core/security/audit.py

audit.py — Append-only audit log with hash-chain integrity.

Every security-relevant event is recorded as a JSONL row that carries:

    - timestamp (UTC ISO8601)
...

**Lines:** 272 | **Size:** 9,632 bytes

## Used By

- [[core-security-cli-py]]
- [[scripts-security_smoke_test-py]]

## Contains

- **class** [[core-security-audit-py-AuditEvent]] — 2 methods
- **class** [[core-security-audit-py-AuditLog]] — 8 methods
- **fn** [[core-security-audit-py-_hash_row]]`(row) → str`
- **fn** [[core-security-audit-py-_new_event_id]]`() → str`

## Import Statements

```python
from __future__ import annotations
import hashlib
import json
import time
import uuid
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import Iterable
```
