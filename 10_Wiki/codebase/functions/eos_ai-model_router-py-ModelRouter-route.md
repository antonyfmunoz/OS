---
type: codebase-function
file: eos_ai/model_router.py
line: 385
generated: 2026-04-11
---

# ModelRouter.route

**File:** [[eos_ai-model_router-py]] | **Line:** 385
**Signature:** `route(task_type, prefer_fast, prefer_cheap) → ModelConfig | None`

**Class:** [[eos_ai-model_router-py-ModelRouter]]

Select the best available model for the given task type.

Falls back to any available model if no specialist is found.
Default priority: Claude first, then by cost.
