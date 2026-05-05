---
type: codebase-function
file: scripts/sandbox_safety_verifier.py
line: 248
generated: 2026-04-12
---

# check_neon_audit_disabled_in_sandbox

**File:** [[scripts-sandbox_safety_verifier-py]] | **Line:** 248
**Signature:** `check_neon_audit_disabled_in_sandbox() → None`

_emit_neon must be a no-op in sandbox mode even when a sandbox
action produces a log record.

## Calls

- [[core-environment-py-Environment-cleanup]]
- [[core-environment-py-make_sandbox]]
- [[scripts-action_system-py-ActionSystem-execute]]
- [[scripts-action_system-py-ActionSystem-propose]]
- [[scripts-sandbox_safety_verifier-py-_assert]]
