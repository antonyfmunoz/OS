---
type: codebase-file
path: core/environment_bridge/w0_packet_builder.py
module: core.environment_bridge.w0_packet_builder
lines: 269
size: 9785
generated: 2026-05-07
---

# core/environment_bridge/w0_packet_builder.py

W0-001 packet builder for the Environment Bridge.

Generates the W0-001 CU rerun packet with all required routing fields
so the local worker validates without manual patching.

...

**Lines:** 269 | **Size:** 9,785 bytes

## Depends On

- [[core-coherence-spine_lineage_contracts-py]]

## Used By

- [[scripts-validate_w0_coherence_dry-py]]

## Contains

- **fn** [[core-environment_bridge-w0_packet_builder-py-_build_w0_001_coherence_envelope]]`() → dict[str, Any]`
- **fn** [[core-environment_bridge-w0_packet_builder-py-build_w0_001_packet]]`() → dict[str, Any]`
- **fn** [[core-environment_bridge-w0_packet_builder-py-w0_001_packet_has_required_routing]]`(packet) → list[str]`
- **fn** [[core-environment_bridge-w0_packet_builder-py-w0_001_packet_blocks_playwright]]`(packet) → bool`

## Import Statements

```python
from __future__ import annotations
import uuid
from datetime import datetime
from datetime import timezone
from typing import Any
from core.coherence.spine_lineage_contracts import CoherenceEnvelope
from core.coherence.spine_lineage_contracts import CoherenceStatus
from core.coherence.spine_lineage_contracts import SpineLineage
from core.coherence.spine_lineage_contracts import SpineStage
from core.coherence.spine_lineage_contracts import SpineStageArtifact
from core.coherence.spine_lineage_contracts import SpineStageStatus
from execution_binding_contracts import build_w0_chrome_gws_binding
from work_packet import WorkPacket
from work_packet import WorkPacketRiskLevel
from work_packet import WorkPacketStatus
```
