---
type: codebase-function
file: eos_ai/substrate/execution_router.py
line: 56
generated: 2026-05-07
---

# ExecutionRouter.route

**File:** [[eos_ai-substrate-execution_router-py]] | **Line:** 56
**Signature:** `route(context) → RoutingDecision`

**Class:** [[eos_ai-substrate-execution_router-py-ExecutionRouter]]

Route an execution request to the best available node.

Args:
    context: Immutable routing parameters describing what is needed.

...

## Calls

- [[eos_ai-substrate-execution_router-py-ExecutionRouter-_capable_nodes]]
- [[eos_ai-substrate-execution_router-py-ExecutionRouter-_decision]]
- [[eos_ai-substrate-execution_router-py-ExecutionRouter-_local_fallback]]
- [[eos_ai-substrate-execution_router-py-ExecutionRouter-_no_route]]
- [[eos_ai-substrate-execution_router-py-ExecutionRouter-_prefer_role]]
- [[eos_ai-substrate-nodes-py-NodeRegistry-get]]

## Called By

- [[eos_ai-substrate-execution_authority-py-ExecutionAuthority-make_handler]]
