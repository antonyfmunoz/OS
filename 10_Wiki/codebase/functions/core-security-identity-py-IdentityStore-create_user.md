---
type: codebase-function
file: core/security/identity.py
line: 174
generated: 2026-04-12
---

# IdentityStore.create_user

**File:** [[core-security-identity-py]] | **Line:** 174
**Signature:** `create_user(user_id, role) → tuple[User, str]`

**Class:** [[core-security-identity-py-IdentityStore]]

Create a user. Returns (user, raw_api_key).

If `api_key` is None, one is generated. The returned raw key is
the ONLY time the plaintext is available — the store persists
only the hash.

## Calls

- [[core-security-identity-py-IdentityStore-_append_user]]
- [[core-security-identity-py-IdentityStore-get_user]]
- [[core-security-identity-py-_hash_api_key]]

## Called By

- [[core-security-cli-py-cmd_user_create]]
- [[scripts-security_smoke_test-py-test_action_system_integration]]
- [[scripts-security_smoke_test-py-test_identity]]
- [[scripts-security_smoke_test-py-test_security_context]]
