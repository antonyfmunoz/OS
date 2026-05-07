---
type: codebase-file
path: core/coherence/spine_coherence_validator.py
module: core.coherence.spine_coherence_validator
lines: 234
size: 9526
generated: 2026-05-07
---

# core/coherence/spine_coherence_validator.py

Canonical Spine Coherence Validator.

Validates that a CoherenceEnvelope represents valid, complete
lineage through the 15-stage UMH canonical spine.

...

**Lines:** 234 | **Size:** 9,526 bytes

## Used By

- [[core-environment_bridge-packet_validator-py]]

## Contains

- **fn** [[core-coherence-spine_coherence_validator-py-validate_coherence_envelope]]`(envelope) → CoherenceValidationResult`
- **fn** [[core-coherence-spine_coherence_validator-py-validate_coherence_envelope_dict]]`(envelope_dict) → CoherenceValidationResult`
- **fn** [[core-coherence-spine_coherence_validator-py-_check_required_stages]]`(lineage, result) → None`
- **fn** [[core-coherence-spine_coherence_validator-py-_check_no_duplicates]]`(lineage, result) → None`
- **fn** [[core-coherence-spine_coherence_validator-py-_check_stage_order]]`(lineage, result) → None`
- **fn** [[core-coherence-spine_coherence_validator-py-_check_stage_artifacts]]`(lineage, result) → None`
- **fn** [[core-coherence-spine_coherence_validator-py-_check_mvp_stubs]]`(lineage, result) → None`
- **fn** [[core-coherence-spine_coherence_validator-py-_check_ordering_constraints]]`(lineage, result) → None`

## Import Statements

```python
from __future__ import annotations
from spine_lineage_contracts import CANONICAL_STAGE_ORDER
from spine_lineage_contracts import REQUIRED_STAGE_NAMES
from spine_lineage_contracts import CoherenceEnvelope
from spine_lineage_contracts import CoherenceFailureReason
from spine_lineage_contracts import CoherenceStatus
from spine_lineage_contracts import CoherenceValidationResult
from spine_lineage_contracts import SpineLineage
from spine_lineage_contracts import SpineStage
from spine_lineage_contracts import SpineStageArtifact
from spine_lineage_contracts import SpineStageStatus
```
