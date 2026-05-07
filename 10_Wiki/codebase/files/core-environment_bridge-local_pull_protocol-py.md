---
type: codebase-file
path: core/environment_bridge/local_pull_protocol.py
module: core.environment_bridge.local_pull_protocol
lines: 257
size: 7685
generated: 2026-05-07
---

# core/environment_bridge/local_pull_protocol.py

Local pull protocol for the Environment Bridge.

Pull-based packet execution: local worker polls a queue for approved
packets, claims them, executes locally, writes results back. This
avoids reliance on VPS SSH push, which can be blocked by sandbox
...

**Lines:** 257 | **Size:** 7,685 bytes

## Contains

- **class** [[core-environment_bridge-local_pull_protocol-py-LocalPullStatus]] — 0 methods
- **class** [[core-environment_bridge-local_pull_protocol-py-TransportStrategy]] — 0 methods
- **class** [[core-environment_bridge-local_pull_protocol-py-LocalPullCycleResult]] — 1 methods
- **fn** [[core-environment_bridge-local_pull_protocol-py-_now_iso]]`() → str`
- **fn** [[core-environment_bridge-local_pull_protocol-py-discover_remote_packets]]`(remote_outbox, force_available) → list[str]`
- **fn** [[core-environment_bridge-local_pull_protocol-py-copy_remote_packet_to_local]]`(remote_path, local_inbox, force_success) → str | None`
- **fn** [[core-environment_bridge-local_pull_protocol-py-claim_local_packet]]`(packet_path) → dict[str, Any] | None`
- **fn** [[core-environment_bridge-local_pull_protocol-py-mark_packet_running]]`(packet_path) → bool`
- **fn** [[core-environment_bridge-local_pull_protocol-py-mark_packet_completed]]`(packet_path) → bool`
- **fn** [[core-environment_bridge-local_pull_protocol-py-mark_packet_failed]]`(packet_path, error) → bool`
- **fn** [[core-environment_bridge-local_pull_protocol-py-write_local_result]]`(results_dir, packet_id, result_data) → str | None`
- **fn** [[core-environment_bridge-local_pull_protocol-py-sync_local_results_to_remote]]`(local_results_dir, remote_results_dir, force_success) → list[str]`
- **fn** [[core-environment_bridge-local_pull_protocol-py-run_local_pull_cycle]]`(remote_outbox, local_inbox, local_results_dir, force_remote_available, force_local_available, validator_fn) → LocalPullCycleResult`
- **fn** [[core-environment_bridge-local_pull_protocol-py-_update_packet_status]]`(packet_path, status, error) → bool`

## Import Statements

```python
from __future__ import annotations
import json
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from pathlib import Path
from typing import Any
from work_packet import WorkPacket
from work_packet import WorkPacketStatus
```
