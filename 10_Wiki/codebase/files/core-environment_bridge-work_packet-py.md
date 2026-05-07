---
type: codebase-file
path: core/environment_bridge/work_packet.py
module: core.environment_bridge.work_packet
lines: 207
size: 7782
generated: 2026-05-07
---

# core/environment_bridge/work_packet.py

Work Packet contract for the Environment Bridge.

Structured, governed work packets that flow between VPS orchestrator
and local execution environments. Every packet carries its own
approval status, risk level, allowed/blocked actions, and proof
...

**Lines:** 207 | **Size:** 7,782 bytes

## Contains

- **class** [[core-environment_bridge-work_packet-py-WorkPacketStatus]] — 0 methods
- **class** [[core-environment_bridge-work_packet-py-WorkPacketRiskLevel]] — 0 methods
- **class** [[core-environment_bridge-work_packet-py-WorkPacketExecutionEnvironment]] — 0 methods
- **class** [[core-environment_bridge-work_packet-py-WorkPacket]] — 1 methods
- **fn** [[core-environment_bridge-work_packet-py-build_work_packet]]`(packet_id, work_order_id, title, description, action_type, target_environment, risk_level, approval_status, founder_confirmation_required, allowed_actions, blocked_actions, expected_outputs, proof_requirements, timeout_seconds) → WorkPacket`
- **fn** [[core-environment_bridge-work_packet-py-work_packet_requires_approval]]`(packet) → bool`
- **fn** [[core-environment_bridge-work_packet-py-work_packet_is_executable]]`(packet) → bool`
- **fn** [[core-environment_bridge-work_packet-py-work_packet_targets_local_gui]]`(packet) → bool`
- **fn** [[core-environment_bridge-work_packet-py-work_packet_blocks_if_unapproved]]`(packet) → bool`
- **fn** [[core-environment_bridge-work_packet-py-summarize_work_packet]]`(packet) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
```
