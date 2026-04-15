---
type: codebase-function
file: scripts/sandbox_safety_verifier.py
line: 106
generated: 2026-04-12
---

# check_sandbox_edit_does_not_touch_production

**File:** [[scripts-sandbox_safety_verifier-py]] | **Line:** 106
**Signature:** `check_sandbox_edit_does_not_touch_production() → None`

Edit a file through ActionSystem in a sandbox, confirm prod is
byte-for-byte identical afterward.

## Calls

- [[core-environment-py-Environment-cleanup]]
- [[core-environment-py-make_sandbox]]
- [[scripts-action_system-py-ActionSystem-execute]]
- [[scripts-action_system-py-ActionSystem-propose]]
- [[scripts-sandbox_safety_verifier-py-_assert]]
