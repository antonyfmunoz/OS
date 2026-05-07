---
type: codebase-file
path: core/environment_bridge/bootstrap_status.py
module: core.environment_bridge.bootstrap_status
lines: 145
size: 4985
generated: 2026-05-07
---

# core/environment_bridge/bootstrap_status.py

Bootstrap status checker for the Environment Bridge.

Evaluates whether the local worker bridge has been bootstrapped by
checking for queue directories, heartbeat, and worker readiness on
both VPS and local sides.
...

**Lines:** 145 | **Size:** 4,985 bytes

## Contains

- **class** [[core-environment_bridge-bootstrap_status-py-BootstrapCheckStatus]] — 0 methods
- **class** [[core-environment_bridge-bootstrap_status-py-BootstrapStatusReport]] — 1 methods
- **fn** [[core-environment_bridge-bootstrap_status-py-check_vps_bootstrap_readiness]]`(packet_filename) → BootstrapStatusReport`
- **fn** [[core-environment_bridge-bootstrap_status-py-bootstrap_status_blocks_dispatch]]`(report) → bool`
- **fn** [[core-environment_bridge-bootstrap_status-py-summarize_bootstrap_status]]`(report) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from pathlib import Path
from typing import Any
from queue_paths import build_vps_queue_paths
```
