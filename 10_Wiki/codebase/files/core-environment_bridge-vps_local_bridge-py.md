---
type: codebase-file
path: core/environment_bridge/vps_local_bridge.py
module: core.environment_bridge.vps_local_bridge
lines: 145
size: 5126
generated: 2026-05-07
---

# core/environment_bridge/vps_local_bridge.py

VPS ↔ Local Worker bridge for the Environment Bridge.

Orchestrates the connection between VPS orchestrator and local Windows
worker. Primary mode is LOCAL_PULL_PRIMARY — the local worker polls
for packets. SSH push exists as optional fallback.
...

**Lines:** 145 | **Size:** 5,126 bytes

## Contains

- **class** [[core-environment_bridge-vps_local_bridge-py-BridgeMode]] — 0 methods
- **class** [[core-environment_bridge-vps_local_bridge-py-VPSLocalBridgeStatus]] — 0 methods
- **class** [[core-environment_bridge-vps_local_bridge-py-VPSLocalBridge]] — 1 methods
- **fn** [[core-environment_bridge-vps_local_bridge-py-build_vps_local_bridge]]`(worker_heartbeat, ssh_push_available, tmux_surface) → VPSLocalBridge`
- **fn** [[core-environment_bridge-vps_local_bridge-py-evaluate_vps_local_bridge_status]]`(bridge, ssh_reachable, heartbeat_present) → VPSLocalBridge`
- **fn** [[core-environment_bridge-vps_local_bridge-py-bridge_can_dispatch_by_push]]`(bridge) → bool`
- **fn** [[core-environment_bridge-vps_local_bridge-py-bridge_can_dispatch_by_pull]]`(bridge) → bool`
- **fn** [[core-environment_bridge-vps_local_bridge-py-bridge_requires_manual_bootstrap]]`(bridge) → bool`
- **fn** [[core-environment_bridge-vps_local_bridge-py-summarize_vps_local_bridge]]`(bridge) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from queue_paths import QueuePaths
from queue_paths import build_vps_queue_paths
from queue_paths import build_local_queue_paths
from heartbeat import WorkerHeartbeat
from heartbeat import WorkerHeartbeatStatus
from heartbeat import heartbeat_is_stale
```
