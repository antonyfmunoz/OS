---
type: codebase-function
file: core/security/identity.py
line: 251
generated: 2026-04-12
---

# IdentityStore.authenticate

**File:** [[core-security-identity-py]] | **Line:** 251
**Signature:** `authenticate(user_id, api_key) → Token`

**Class:** [[core-security-identity-py-IdentityStore]]

Verify credentials and return a signed token.

Raises AuthError on any failure — unknown user, wrong key,
disabled account. The message is intentionally generic so
enumeration is harder.

## Calls

- [[core-security-identity-py-IdentityStore-_issue_token]]
- [[core-security-identity-py-IdentityStore-get_user]]
- [[core-security-identity-py-_hash_api_key]]

## Called By

- [[core-security-cli-py-cmd_user_auth]]
- [[scripts-security_smoke_test-py-test_action_system_integration]]
- [[scripts-security_smoke_test-py-test_identity]]
- [[scripts-security_smoke_test-py-test_security_context]]
