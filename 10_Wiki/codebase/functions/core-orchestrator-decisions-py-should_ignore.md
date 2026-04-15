---
type: codebase-function
file: core/orchestrator/decisions.py
line: 137
generated: 2026-04-12
---

# should_ignore

**File:** [[core-orchestrator-decisions-py]] | **Line:** 137
**Signature:** `should_ignore(action) → bool`

True if this action can be silently dropped without human attention.

Current rule: the only thing we ignore is an idempotency_skip
synthetic action whose result already reports ok=True. Everything
else either retries or escalates.

## Calls

- [[core-orchestrator-decisions-py-_action_type]]
