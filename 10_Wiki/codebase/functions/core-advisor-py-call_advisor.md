---
type: codebase-function
file: core/advisor.py
line: 363
generated: 2026-05-07
---

# call_advisor

**File:** [[core-advisor-py]] | **Line:** 363
**Signature:** `call_advisor(task, executor_output, context, metadata) → AdvisorResult`

Call the advisor model for guidance on an executor result.

The advisor receives:
  - the original task
  - the executor's output
...

## Calls

- [[core-advisor-py-_RateLimiter-allow]]
- [[core-advisor-py-_build_advisor_prompt]]
- [[core-advisor-py-_check_workflow_budget]]
- [[core-advisor-py-_increment_workflow_count]]
- [[core-advisor-py-_log_advisor_call]]
- [[core-advisor-py-_parse_advisor_response]]

## Called By

- [[core-advisor-py-run_with_advisor]]
