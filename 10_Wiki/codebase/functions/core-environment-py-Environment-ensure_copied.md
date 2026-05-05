---
type: codebase-function
file: core/environment.py
line: 234
generated: 2026-04-12
---

# Environment.ensure_copied

**File:** [[core-environment-py]] | **Line:** 234
**Signature:** `ensure_copied(target) → Path`

**Class:** [[core-environment-py-Environment]]

Copy-on-write: if a file exists in production but not yet in
the workspace, copy it over so edits/snapshots have a baseline.

Returns the mapped workspace path. Safe to call for files that
don't exist — it simply does nothing in that case.

## Calls

- [[core-environment-py-Environment-_to_rel]]
- [[core-environment-py-Environment-resolve]]

## Called By

- [[scripts-action_system-py-ActionSystem-_resolve_target]]
