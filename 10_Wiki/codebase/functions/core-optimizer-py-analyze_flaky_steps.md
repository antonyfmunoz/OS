---
type: codebase-function
file: core/optimizer.py
line: 141
generated: 2026-05-07
---

# analyze_flaky_steps

**File:** [[core-optimizer-py]] | **Line:** 141
**Signature:** `analyze_flaky_steps(ctx) → list[Proposal]`

Identify steps that retried more than once on average.

Evidence: workflow_log.jsonl rows with event=step_retry grouped by
(workflow_name, step_id).

## Calls

- [[core-optimizer-py-_new_id]]
