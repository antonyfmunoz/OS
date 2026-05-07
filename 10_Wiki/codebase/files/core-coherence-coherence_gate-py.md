---
type: codebase-file
path: core/coherence/coherence_gate.py
module: core.coherence.coherence_gate
lines: 75
size: 2300
generated: 2026-05-07
---

# core/coherence/coherence_gate.py

Coherence Gate — fail-closed execution guard.

No work packet executes without passing the coherence gate.
The gate verifies that the packet has a valid CoherenceEnvelope
proving it descended from the canonical UMH spine.
...

**Lines:** 75 | **Size:** 2,300 bytes

## Used By

- [[scripts-validate_w0_coherence_dry-py]]

## Contains

- **class** [[core-coherence-coherence_gate-py-CoherenceGateBlocked]] — 1 methods
- **fn** [[core-coherence-coherence_gate-py-evaluate_coherence_before_execution]]`(packet) → CoherenceValidationResult`
- **fn** [[core-coherence-coherence_gate-py-assert_coherent_or_block]]`(packet) → None`
- **fn** [[core-coherence-coherence_gate-py-coherence_gate_allows_execution]]`(packet) → tuple[bool, CoherenceValidationResult]`

## Import Statements

```python
from __future__ import annotations
from typing import Any
from spine_coherence_validator import validate_coherence_envelope
from spine_coherence_validator import validate_coherence_envelope_dict
from spine_lineage_contracts import CoherenceEnvelope
from spine_lineage_contracts import CoherenceStatus
from spine_lineage_contracts import CoherenceValidationResult
```
