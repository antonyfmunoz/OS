---
type: codebase-function
file: core/action_system/deferred_status.py
line: 124
generated: 2026-04-12
---

# wake_due_snoozed

**File:** [[core-action_system-deferred_status-py]] | **Line:** 124
**Signature:** `wake_due_snoozed(now) → list[str]`

Promote snoozed deferred actions whose snoozed_until has passed.

Scans every `.status.json` sidecar in DEFERRED_DIR. For any record
with `status == "snoozed"` and a `snoozed_until` timestamp in the
past, rewrites the sidecar to `status="pending"` with a note
...

## Calls

- [[core-action_system-deferred_status-py-read_status]]
- [[core-action_system-deferred_status-py-write_status]]

## Called By

- [[scripts-deferred-py-cmd_wake]]
