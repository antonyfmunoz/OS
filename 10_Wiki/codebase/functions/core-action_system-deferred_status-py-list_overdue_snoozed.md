---
type: codebase-function
file: core/action_system/deferred_status.py
line: 173
generated: 2026-05-07
---

# list_overdue_snoozed

**File:** [[core-action_system-deferred_status-py]] | **Line:** 173
**Signature:** `list_overdue_snoozed(now) → list[str]`

Return action ids that are snoozed and whose wake time has passed.

Read-only companion to `wake_due_snoozed` — used by the deferred
CLI's `list --overdue-snoozed` filter and the `wake --dry-run` flag.

## Calls

- [[core-action_system-deferred_status-py-read_status]]

## Called By

- [[scripts-deferred-py-cmd_list]]
- [[scripts-deferred-py-cmd_wake]]
