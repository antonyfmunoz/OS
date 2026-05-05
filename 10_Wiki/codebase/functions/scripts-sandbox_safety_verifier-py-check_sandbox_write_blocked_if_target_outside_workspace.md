---
type: codebase-function
file: scripts/sandbox_safety_verifier.py
line: 138
generated: 2026-04-12
---

# check_sandbox_write_blocked_if_target_outside_workspace

**File:** [[scripts-sandbox_safety_verifier-py]] | **Line:** 138
**Signature:** `check_sandbox_write_blocked_if_target_outside_workspace() → None`

If someone hand-rolls an ActionSystem call targeting a
production absolute path, guard_write must catch it.

## Calls

- [[core-environment-py-Environment-cleanup]]
- [[core-environment-py-Environment-guard_write]]
- [[core-environment-py-make_sandbox]]
