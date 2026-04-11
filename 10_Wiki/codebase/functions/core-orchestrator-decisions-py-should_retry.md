---
type: codebase-function
file: core/orchestrator/decisions.py
line: 102
generated: 2026-04-11
---

# should_retry

**File:** [[core-orchestrator-decisions-py]] | **Line:** 102
**Signature:** `should_retry(action) → bool`

True if this failed action can be safely re-run automatically.

Rules (all must hold):
  1. Action type is in RETRY_ELIGIBLE_TYPES.
  2. Action has an idempotency key (so a retry is a no-op if the
...

## Calls

- [[core-orchestrator-decisions-py-_action_type]]
- [[core-orchestrator-decisions-py-_has_idempotency]]
- [[core-orchestrator-decisions-py-_risk]]
- [[core-orchestrator-decisions-py-retry_count_today]]

## Called By

- [[core-orchestrator-decisions-py-should_escalate]]
