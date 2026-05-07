---
type: codebase-file
path: core/environment_bridge/queue_paths.py
module: core.environment_bridge.queue_paths
lines: 102
size: 2477
generated: 2026-05-07
---

# core/environment_bridge/queue_paths.py

Queue paths for the Environment Bridge.

Canonical filesystem paths for work packet queues on VPS and local
worker environments. Pure path construction — no I/O in tests.

...

**Lines:** 102 | **Size:** 2,477 bytes

## Contains

- **class** [[core-environment_bridge-queue_paths-py-QueuePaths]] — 1 methods
- **fn** [[core-environment_bridge-queue_paths-py-build_vps_queue_paths]]`() → QueuePaths`
- **fn** [[core-environment_bridge-queue_paths-py-build_local_queue_paths]]`() → QueuePaths`
- **fn** [[core-environment_bridge-queue_paths-py-ensure_queue_paths]]`(paths) → list[str]`
- **fn** [[core-environment_bridge-queue_paths-py-queue_paths_are_valid]]`(paths) → bool`
- **fn** [[core-environment_bridge-queue_paths-py-summarize_queue_paths]]`(paths) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any
```
