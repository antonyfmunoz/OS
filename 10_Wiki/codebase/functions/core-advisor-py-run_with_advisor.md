---
type: codebase-function
file: core/advisor.py
line: 463
generated: 2026-04-12
---

# run_with_advisor

**File:** [[core-advisor-py]] | **Line:** 463
**Signature:** `run_with_advisor(task, context, metadata) → dict[str, Any]`

Unified execution interface with conditional advisor escalation.

Flow:
  1. If executor_result not provided, call executor_fn(task, context)
  2. Evaluate result with needs_advisor()
...

## Calls

- [[core-advisor-py-AdvisorResult-to_canonical]]
- [[core-advisor-py-AdvisorResult-to_dict]]
- [[core-advisor-py-_extract_output_text]]
- [[core-advisor-py-call_advisor]]
- [[core-advisor-py-needs_advisor]]
