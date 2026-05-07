---
type: codebase-function
file: core/context.py
line: 104
generated: 2026-05-07
---

# apply_context

**File:** [[core-context-py]] | **Line:** 104
**Signature:** `apply_context(composition, context) → ContextualComposition`

Apply L1 context to an L2 composition.

Returns a ContextualComposition that wraps the original with
context metadata.  The composition's primitive tags are frozen
at call time — any subsequent mutation that changes them will
...

## Called By

- [[core-composer-py-compose]]
