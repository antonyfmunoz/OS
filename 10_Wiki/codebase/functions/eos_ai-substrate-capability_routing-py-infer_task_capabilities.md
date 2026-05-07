---
type: codebase-function
file: eos_ai/substrate/capability_routing.py
line: 75
generated: 2026-05-07
---

# infer_task_capabilities

**File:** [[eos_ai-substrate-capability_routing-py]] | **Line:** 75
**Signature:** `infer_task_capabilities(task) → set[TaskCapability]`

Infer required capabilities from task text. Deterministic keyword matching.

Rules:
- Builder keywords → BUILDER_CONTEXT, else → PRODUCT_CONTEXT
- Heavy/local keywords → LOCAL_COMPUTE + HEAVY_REASONING
...

## Called By

- [[eos_ai-substrate-capability_routing-py-choose_execution_target]]
- [[eos_ai-substrate-capability_routing-py-route_task]]
