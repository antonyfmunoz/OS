---
type: codebase-function
file: eos_ai/substrate/node_controller.py
line: 197
generated: 2026-05-07
---

# route

**File:** [[eos_ai-substrate-node_controller-py]] | **Line:** 197
**Signature:** `route() → RoutingDecision`

Make a routing decision for a task or capability set.

Resolution order:
1. Operator explicit override (session.node_preference == "local" | "vps").
2. Capability requirement — if task needs local-only caps, route local.
...

## Calls

- [[eos_ai-substrate-node_controller-py-_is_http_transport_available]]
- [[eos_ai-substrate-node_controller-py-_is_local_available_via_presence]]
- [[eos_ai-substrate-node_controller-py-_is_local_node_online]]
- [[eos_ai-substrate-node_controller-py-_local_decision]]
- [[eos_ai-substrate-node_controller-py-_log]]
- [[eos_ai-substrate-node_controller-py-_vps_decision]]
