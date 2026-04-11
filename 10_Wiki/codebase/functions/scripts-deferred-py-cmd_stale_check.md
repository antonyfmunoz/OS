---
type: codebase-function
file: scripts/deferred.py
line: 121
generated: 2026-04-11
---

# cmd_stale_check

**File:** [[scripts-deferred-py]] | **Line:** 121
**Signature:** `cmd_stale_check(args) → int`

Scan the queue and mark every pending action older than threshold as stale.

## Calls

- [[core-action_system-deferred_status-py-mark_stale_over_threshold]]
