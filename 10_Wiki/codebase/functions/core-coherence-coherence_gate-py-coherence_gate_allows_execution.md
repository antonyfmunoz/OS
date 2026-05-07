---
type: codebase-function
file: core/coherence/coherence_gate.py
line: 66
generated: 2026-05-07
---

# coherence_gate_allows_execution

**File:** [[core-coherence-coherence_gate-py]] | **Line:** 66
**Signature:** `coherence_gate_allows_execution(packet) → tuple[bool, CoherenceValidationResult]`

Check if the coherence gate allows execution.

Returns (allowed, result) tuple. Does not raise.

## Calls

- [[core-coherence-coherence_gate-py-evaluate_coherence_before_execution]]

## Called By

- [[scripts-validate_w0_coherence_dry-py-run_dry_validation]]
