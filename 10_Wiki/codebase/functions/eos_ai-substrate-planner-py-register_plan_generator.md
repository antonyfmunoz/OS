---
type: codebase-function
file: eos_ai/substrate/planner.py
line: 61
generated: 2026-05-07
---

# register_plan_generator

**File:** [[eos_ai-substrate-planner-py]] | **Line:** 61
**Signature:** `register_plan_generator(intent_type, generator) → None`

Register a plan generator for an intent type.

Generators must be deterministic: same intent + state → same steps.
