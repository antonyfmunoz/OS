---
type: codebase-function
file: scripts/deferred.py
line: 133
generated: 2026-04-11
---

# cmd_prune

**File:** [[scripts-deferred-py]] | **Line:** 133
**Signature:** `cmd_prune(args) → int`

Delete deferred actions that are marked stale (or past threshold).

Two modes:
  --marked-only (default): only prunes actions whose sidecar says `stale`
  --auto-mark: first runs stale-check with --older-than, then prunes

## Calls

- [[core-action_system-deferred-py-delete_deferred]]
- [[core-action_system-deferred-py-list_deferred]]
- [[core-action_system-deferred_status-py-clear_status]]
- [[core-action_system-deferred_status-py-mark_stale_over_threshold]]
- [[core-action_system-deferred_status-py-read_status]]
