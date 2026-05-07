---
type: codebase-function
file: core/coherence/coherence_gate.py
line: 53
generated: 2026-05-07
---

# assert_coherent_or_block

**File:** [[core-coherence-coherence_gate-py]] | **Line:** 53
**Signature:** `assert_coherent_or_block(packet) → None`

Assert that a packet is coherent or raise CoherenceGateBlocked.

Call this before any execution. If the packet is not coherent,
raises CoherenceGateBlocked with full diagnostic.

## Calls

- [[core-coherence-coherence_gate-py-evaluate_coherence_before_execution]]
