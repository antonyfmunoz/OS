---
type: codebase-function
file: core/advisor.py
line: 274
generated: 2026-04-12
---

# needs_advisor

**File:** [[core-advisor-py]] | **Line:** 274
**Signature:** `needs_advisor(result, context, metadata) → tuple[bool, str]`

Evaluate whether an executor result should be escalated to the advisor.

Args:
    result:   the executor's output (string or HarnessResult-like)
    context:  dict with optional keys: graph_hits, step_type, task_description,
...

## Calls

- [[core-advisor-py-_extract_output_text]]
- [[core-capability-py-coerce_risk]]

## Called By

- [[core-advisor-py-run_with_advisor]]
