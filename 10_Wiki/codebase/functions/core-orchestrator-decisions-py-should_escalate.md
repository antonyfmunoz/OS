---
type: codebase-function
file: core/orchestrator/decisions.py
line: 125
generated: 2026-04-12
---

# should_escalate

**File:** [[core-orchestrator-decisions-py]] | **Line:** 125
**Signature:** `should_escalate(action) → bool`

True if this failure should surface to a human.

An action escalates when it is NOT retry-eligible — either because
its type is destructive (run_script, write_file), it has no
idempotency guarantee, it is high-risk, or it has already burned
...

## Calls

- [[core-orchestrator-decisions-py-should_retry]]
