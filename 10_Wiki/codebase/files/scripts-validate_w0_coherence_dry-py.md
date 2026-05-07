---
type: codebase-file
path: scripts/validate_w0_coherence_dry.py
module: scripts.validate_w0_coherence_dry
lines: 238
size: 8532
tags: [entry-point]
generated: 2026-05-07
---

# scripts/validate_w0_coherence_dry.py

> **ENTRY POINT** — Contains `if __name__` or server start.

W0 Dry Validation with Coherence Envelope.

Generates the W0-001 packet and validates it through every gate
without executing any actions, launching any GUI, or accessing
any external service.
...

**Lines:** 238 | **Size:** 8,532 bytes

## Depends On

- [[core-coherence-coherence_gate-py]]
- [[core-coherence-spine_lineage_contracts-py]]
- [[core-environment_bridge-execution_binding_validator-py]]
- [[core-environment_bridge-packet_validator-py]]
- [[core-environment_bridge-w0_packet_builder-py]]

## Contains

- **fn** [[scripts-validate_w0_coherence_dry-py-run_dry_validation]]`() → dict`
- **fn** [[scripts-validate_w0_coherence_dry-py-_write_report]]`(results) → None`

## Import Statements

```python
import json
import sys
from datetime import datetime
from datetime import timezone
from pathlib import Path
from core.coherence.coherence_gate import coherence_gate_allows_execution
from core.coherence.coherence_gate import evaluate_coherence_before_execution
from core.coherence.spine_lineage_contracts import CoherenceStatus
from core.coherence.spine_lineage_contracts import SpineStage
from core.coherence.spine_lineage_contracts import SpineStageStatus
from core.environment_bridge.execution_binding_validator import validate_execution_binding_dict
from core.environment_bridge.packet_validator import validate_w0_packet_dict
from core.environment_bridge.w0_packet_builder import build_w0_001_packet
```
