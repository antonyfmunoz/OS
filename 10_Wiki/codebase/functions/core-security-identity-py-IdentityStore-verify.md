---
type: codebase-function
file: core/security/identity.py
line: 265
generated: 2026-04-12
---

# IdentityStore.verify

**File:** [[core-security-identity-py]] | **Line:** 265
**Signature:** `verify(token_str) → Token`

**Class:** [[core-security-identity-py-IdentityStore]]

Parse + verify a token string. Raises AuthError on any failure.

## Calls

- [[core-security-identity-py-IdentityStore-_load_secret]]
- [[core-security-identity-py-IdentityStore-_revoked_jtis]]
- [[core-security-identity-py-IdentityStore-get_user]]
- [[core-security-identity-py-_b64url_decode]]

## Called By

- [[scripts-security_smoke_test-py-test_identity]]
