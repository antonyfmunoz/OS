---
type: codebase-function
file: eos_ai/substrate/capability_routing_contracts.py
line: 85
generated: 2026-05-07
---

# score_node_for_requirement

**File:** [[eos_ai-substrate-capability_routing_contracts-py]] | **Line:** 85
**Signature:** `score_node_for_requirement(node, requirement) → tuple[float, list[str]]`

Score a node against a routing requirement.

Returns (score, missing_capabilities).
Score range: 0.0 (unusable) to 1.0 (perfect match).
A node missing any required capability scores 0.0.

## Calls

- [[eos_ai-substrate-topology_contracts-py-NodeProfile-has_capability]]

## Called By

- [[eos_ai-substrate-capability_routing_contracts-py-choose_best_node]]
