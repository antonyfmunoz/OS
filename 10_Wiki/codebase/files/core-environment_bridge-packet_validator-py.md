---
type: codebase-file
path: core/environment_bridge/packet_validator.py
module: core.environment_bridge.packet_validator
lines: 275
size: 10098
generated: 2026-05-07
---

# core/environment_bridge/packet_validator.py

Packet validator for the Environment Bridge.

Validates work packets before execution. Catches missing approvals,
expired packets, blocked action violations, missing governance,
missing proof requirements, and missing/invalid execution bindings.
...

**Lines:** 275 | **Size:** 10,098 bytes

## Depends On

- [[core-coherence-spine_coherence_validator-py]]

## Used By

- [[scripts-validate_w0_coherence_dry-py]]

## Contains

- **class** [[core-environment_bridge-packet_validator-py-PacketValidationStatus]] — 0 methods
- **class** [[core-environment_bridge-packet_validator-py-PacketValidationResult]] — 1 methods
- **fn** [[core-environment_bridge-packet_validator-py-validate_work_packet]]`(packet) → PacketValidationResult`
- **fn** [[core-environment_bridge-packet_validator-py-validate_w0_packet_dict]]`(packet) → PacketValidationResult`
- **fn** [[core-environment_bridge-packet_validator-py-packet_has_required_governance]]`(packet) → bool`
- **fn** [[core-environment_bridge-packet_validator-py-packet_has_required_proof]]`(packet) → bool`
- **fn** [[core-environment_bridge-packet_validator-py-packet_contains_blocked_action_violation]]`(packet) → list[str]`
- **fn** [[core-environment_bridge-packet_validator-py-packet_validator_blocks_execution]]`(result) → bool`
- **fn** [[core-environment_bridge-packet_validator-py-packet_requires_environment_adapter]]`(packet) → bool`
- **fn** [[core-environment_bridge-packet_validator-py-packet_requires_human_approval_adapter]]`(packet) → bool`
- **fn** [[core-environment_bridge-packet_validator-py-_check_cu_governance]]`(packet) → list[str]`
- **fn** [[core-environment_bridge-packet_validator-py-packet_requires_mastery]]`(packet) → bool`
- **fn** [[core-environment_bridge-packet_validator-py-packet_requires_worker_runtime]]`(packet) → bool`
- **fn** [[core-environment_bridge-packet_validator-py-_check_routing_fields]]`(packet) → list[str]`
- **fn** [[core-environment_bridge-packet_validator-py-_check_adapter_boundary]]`(packet) → list[str]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
from core.coherence.spine_coherence_validator import validate_coherence_envelope_dict
from execution_binding_validator import validate_execution_binding_dict
from work_packet import WorkPacket
from work_packet import WorkPacketRiskLevel
from work_packet import WorkPacketStatus
from work_packet import work_packet_targets_local_gui
```
