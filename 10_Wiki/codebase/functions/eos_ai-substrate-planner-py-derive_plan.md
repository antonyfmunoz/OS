---
type: codebase-function
file: eos_ai/substrate/planner.py
line: 205
generated: 2026-05-07
---

# derive_plan

**File:** [[eos_ai-substrate-planner-py]] | **Line:** 205
**Signature:** `derive_plan(intent, state) → Plan | None`

Derive a plan for the given intent.

Returns None if no generator is registered for the intent type.
Deterministic: same intent + state → same Plan.

## Calls

- [[eos_ai-substrate-decision_engine-py-_log]]
- [[eos_ai-substrate-planner-py-_log]]
- [[eos_ai-substrate-planner-py-get_plan_generator]]

## Called By

- [[eos_ai-substrate-planner-py-PlannerStrategy-evaluate]]
