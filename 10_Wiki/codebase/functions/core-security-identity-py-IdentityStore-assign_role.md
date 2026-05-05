---
type: codebase-function
file: core/security/identity.py
line: 202
generated: 2026-04-12
---

# IdentityStore.assign_role

**File:** [[core-security-identity-py]] | **Line:** 202
**Signature:** `assign_role(user_id, role) → User`

**Class:** [[core-security-identity-py-IdentityStore]]

Append a new record with the updated role. History preserved.

## Calls

- [[core-security-identity-py-IdentityStore-_append_user]]
- [[core-security-identity-py-IdentityStore-get_user]]

## Called By

- [[core-security-cli-py-cmd_user_role]]
- [[scripts-security_smoke_test-py-test_identity]]
