---
type: codebase-function
file: core/optimizer.py
line: 367
generated: 2026-05-07
---

# analyze_advisor_effectiveness

**File:** [[core-optimizer-py]] | **Line:** 367
**Signature:** `analyze_advisor_effectiveness(ctx) → list[Proposal]`

Analyze advisor usage patterns and suggest rule tuning.

Reads the advisor log to measure:
  - How often the advisor is triggered
  - Which escalation reasons dominate
...

## Calls

- [[core-optimizer-py-_new_id]]
- [[core-optimizer-py-_read_jsonl]]
