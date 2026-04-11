---
type: codebase-function
file: eos_ai/model_router.py
line: 449
generated: 2026-04-11
---

# ModelRouter.call_with_fallback

**File:** [[eos_ai-model_router-py]] | **Line:** 449
**Signature:** `call_with_fallback(task_type, prompt, system, max_tokens) → str`

**Class:** [[eos_ai-model_router-py-ModelRouter]]

Try models in priority order until one returns a non-empty response.

Use this instead of route() + call() when you need automatic fallback.
Marks models unavailable after confirmed failures so routing improves
over the session.

## Calls

- [[eos_ai-model_router-py-ModelRouter-call]]

## Called By

- [[scripts-substrate_router_claude_primary_smoke_test-py-main]]
