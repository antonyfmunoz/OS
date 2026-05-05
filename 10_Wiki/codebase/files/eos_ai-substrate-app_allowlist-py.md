---
type: codebase-file
path: eos_ai/substrate/app_allowlist.py
module: eos_ai.substrate.app_allowlist
lines: 71
size: 2162
generated: 2026-04-12
---

# eos_ai/substrate/app_allowlist.py

App launch allow-list for LAUNCH_APP actions.

The substrate's trust boundary forbids raw executable paths and arbitrary
shell. The daemon is only allowed to launch apps whose `app_id` appears in
this allow-list, and only by probing the declared candidate binaries with
...

**Lines:** 71 | **Size:** 2,162 bytes

## Used By

- [[eos_ai-substrate-station_daemon-py]]

## Contains

- **class** [[eos_ai-substrate-app_allowlist-py-AllowedApp]] — 0 methods
- **fn** [[eos_ai-substrate-app_allowlist-py-resolve_app]]`(app_id) → AllowedApp | None`
- **fn** [[eos_ai-substrate-app_allowlist-py-is_allowed]]`(app_id) → bool`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
```
