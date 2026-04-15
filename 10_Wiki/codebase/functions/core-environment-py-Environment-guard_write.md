---
type: codebase-function
file: core/environment.py
line: 275
generated: 2026-04-12
---

# Environment.guard_write

**File:** [[core-environment-py]] | **Line:** 275
**Signature:** `guard_write(target) → None`

**Class:** [[core-environment-py-Environment]]

Raise PermissionError if this environment is not allowed to
write to `target`. Called by ActionSystem before any mutation.

## Calls

- [[core-environment-py-Environment-resolve]]

## Called By

- [[core-security-environments-py-SecurityEnv-guard_write]]
- [[scripts-action_system-py-ActionSystem-_exec_delete_file]]
- [[scripts-action_system-py-ActionSystem-_exec_edit_file]]
- [[scripts-action_system-py-ActionSystem-_exec_write_file]]
- [[scripts-sandbox_safety_verifier-py-check_guard_blocks_production_paths]]
- [[scripts-sandbox_safety_verifier-py-check_sandbox_write_blocked_if_target_outside_workspace]]
