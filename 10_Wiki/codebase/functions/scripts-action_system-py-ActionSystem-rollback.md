---
type: codebase-function
file: scripts/action_system.py
line: 837
generated: 2026-04-12
---

# ActionSystem.rollback

**File:** [[scripts-action_system-py]] | **Line:** 837
**Signature:** `rollback(action_id) → ActionResult`

**Class:** [[scripts-action_system-py-ActionSystem]]

Undo an earlier file-mutating action by restoring its snapshot.

RUN_SCRIPT and RUN_COMMAND have no automatic rollback — those
are rejected. Callers must compose a compensating action.

## Calls

- [[scripts-action_system-py-ActionSystem-_append_jsonl]]
- [[scripts-action_system-py-ActionSystem-_refresh_graph]]

## Called By

- [[scripts-action_system-py-main]]
