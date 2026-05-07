---
type: codebase-file
path: core/environment_bridge/heartbeat.py
module: core.environment_bridge.heartbeat
lines: 138
size: 4214
generated: 2026-05-07
---

# core/environment_bridge/heartbeat.py

Worker heartbeat for the Environment Bridge.

Tracks local worker liveness via file-based heartbeat. The local
worker writes a heartbeat file periodically; the VPS reads it to
determine if the worker is online/stale/offline.
...

**Lines:** 138 | **Size:** 4,214 bytes

## Contains

- **class** [[core-environment_bridge-heartbeat-py-WorkerHeartbeatStatus]] — 0 methods
- **class** [[core-environment_bridge-heartbeat-py-WorkerHeartbeat]] — 1 methods
- **fn** [[core-environment_bridge-heartbeat-py-build_worker_heartbeat]]`(worker_id, host, environment, tmux_session, capabilities) → WorkerHeartbeat`
- **fn** [[core-environment_bridge-heartbeat-py-heartbeat_is_stale]]`(heartbeat, current_time, threshold_seconds) → bool`
- **fn** [[core-environment_bridge-heartbeat-py-write_heartbeat]]`(path, heartbeat) → bool`
- **fn** [[core-environment_bridge-heartbeat-py-read_heartbeat]]`(path) → WorkerHeartbeat | None`
- **fn** [[core-environment_bridge-heartbeat-py-summarize_heartbeat]]`(heartbeat) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import json
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from pathlib import Path
from typing import Any
```
