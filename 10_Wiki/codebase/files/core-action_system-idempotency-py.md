---
type: codebase-file
path: core/action_system/idempotency.py
module: core.action_system.idempotency
lines: 296
size: 9311
generated: 2026-04-12
---

# core/action_system/idempotency.py

Filesystem sentinel store for Control Plane idempotency.

One JSON file per key at /opt/OS/logs/idempotency/<sha1(key)>.json.

The core contract is exactly one successful execution per key within
...

**Lines:** 296 | **Size:** 9,311 bytes

## Contains

- **class** [[core-action_system-idempotency-py-Sentinel]] — 2 methods
- **fn** [[core-action_system-idempotency-py-_hash_key]]`(key) → str`
- **fn** [[core-action_system-idempotency-py-_path_for]]`(key) → str`
- **fn** [[core-action_system-idempotency-py-_now_iso]]`() → str`
- **fn** [[core-action_system-idempotency-py-read]]`(key) → Sentinel | None`
- **fn** [[core-action_system-idempotency-py-_write]]`(sentinel) → str`
- **fn** [[core-action_system-idempotency-py-claim]]`(key, action_id, ttl_seconds) → tuple[bool, Sentinel]`
- **fn** [[core-action_system-idempotency-py-force_claim]]`(key, action_id, ttl_seconds) → Sentinel`
- **fn** [[core-action_system-idempotency-py-complete]]`(key, status) → Sentinel | None`
- **fn** [[core-action_system-idempotency-py-clear]]`(key) → bool`
- **fn** [[core-action_system-idempotency-py-list_all]]`() → list[Sentinel]`
- **fn** [[core-action_system-idempotency-py-find]]`(key_or_sha) → Sentinel | None`
- **fn** [[core-action_system-idempotency-py-prune_expired]]`() → list[str]`

## Import Statements

```python
from __future__ import annotations
import hashlib
import json
import os
from dataclasses import dataclass
from dataclasses import asdict
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any
```
