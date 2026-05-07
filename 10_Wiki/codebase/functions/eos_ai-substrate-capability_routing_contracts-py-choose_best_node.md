---
type: codebase-function
file: eos_ai/substrate/capability_routing_contracts.py
line: 119
generated: 2026-05-07
---

# choose_best_node

**File:** [[eos_ai-substrate-capability_routing_contracts-py]] | **Line:** 119
**Signature:** `choose_best_node(topology, requirement) → RoutingDecision`

Choose the best node for a routing requirement from a topology.

Returns SETUP_REQUIRED if no node has the required capabilities.

## Calls

- [[eos_ai-substrate-capability_routing_contracts-py-score_node_for_requirement]]
