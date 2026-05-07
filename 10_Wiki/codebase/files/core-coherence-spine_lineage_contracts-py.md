---
type: codebase-file
path: core/coherence/spine_lineage_contracts.py
module: core.coherence.spine_lineage_contracts
lines: 190
size: 6476
generated: 2026-05-07
---

# core/coherence/spine_lineage_contracts.py

Canonical Spine Lineage Contracts.

Typed contracts for the 15-stage UMH canonical spine.
Every executable work packet must prove it descended from
the full spine or an explicitly governed MVP stub lineage.
...

**Lines:** 190 | **Size:** 6,476 bytes

## Used By

- [[core-environment_bridge-w0_packet_builder-py]]
- [[scripts-validate_w0_coherence_dry-py]]

## Contains

- **class** [[core-coherence-spine_lineage_contracts-py-SpineStage]] — 0 methods
- **class** [[core-coherence-spine_lineage_contracts-py-SpineStageStatus]] — 0 methods
- **class** [[core-coherence-spine_lineage_contracts-py-CoherenceStatus]] — 0 methods
- **class** [[core-coherence-spine_lineage_contracts-py-CoherenceFailureReason]] — 0 methods
- **class** [[core-coherence-spine_lineage_contracts-py-SpineStageArtifact]] — 1 methods
- **class** [[core-coherence-spine_lineage_contracts-py-SpineLineage]] — 3 methods
- **class** [[core-coherence-spine_lineage_contracts-py-CoherenceEnvelope]] — 1 methods
- **class** [[core-coherence-spine_lineage_contracts-py-CoherenceValidationResult]] — 1 methods

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Any
```
