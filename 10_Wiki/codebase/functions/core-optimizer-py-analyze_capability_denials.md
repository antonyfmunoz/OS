---
type: codebase-function
file: core/optimizer.py
line: 257
generated: 2026-04-12
---

# analyze_capability_denials

**File:** [[core-optimizer-py]] | **Line:** 257
**Signature:** `analyze_capability_denials(ctx) → list[Proposal]`

When the harness denies capability repeatedly for the same
(agent, operation), propose broadening the profile — but only as
a human-review proposal, never an automatic change.

## Calls

- [[core-optimizer-py-_new_id]]
