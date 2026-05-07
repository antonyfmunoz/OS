---
type: codebase-class
file: eos_ai/substrate/execution_router.py
line: 39
generated: 2026-05-07
---

# ExecutionRouter

**File:** [[eos_ai-substrate-execution_router-py]] | **Line:** 39

Routes execution requests to the best available node.

Stateless decision engine. Re-reads registry state on each call.
Returns immutable RoutingDecision with full rationale.

...

## Methods

- [[eos_ai-substrate-execution_router-py-ExecutionRouter-__init__]]`(registry) → None` — 
- [[eos_ai-substrate-execution_router-py-ExecutionRouter-route]]`(context) → RoutingDecision` — Route an execution request to the best available node.
- [[eos_ai-substrate-execution_router-py-ExecutionRouter-_capable_nodes]]`(required) → list[Node]` — Find nodes that have ALL required capabilities.
- [[eos_ai-substrate-execution_router-py-ExecutionRouter-_prefer_role]]`(nodes, role) → Node | None` — Return first node with given role, else first node in list.
- [[eos_ai-substrate-execution_router-py-ExecutionRouter-_transport_for]]`(node) → str` — Determine transport protocol for a node.
- [[eos_ai-substrate-execution_router-py-ExecutionRouter-_decision]]`(node, context, reason_code, detail) → RoutingDecision` — Build a RoutingDecision with optional fallback info.
- [[eos_ai-substrate-execution_router-py-ExecutionRouter-_local_fallback]]`(context, detail) → RoutingDecision` — Build a vps-primary fallback decision.
- [[eos_ai-substrate-execution_router-py-ExecutionRouter-_no_route]]`(context, detail) → RoutingDecision` — Build an empty-target decision when no route is possible.
