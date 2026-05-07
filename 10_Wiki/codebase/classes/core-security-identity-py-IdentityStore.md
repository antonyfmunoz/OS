---
type: codebase-class
file: core/security/identity.py
line: 122
generated: 2026-05-07
---

# IdentityStore

**File:** [[core-security-identity-py]] | **Line:** 122

File-backed user store + HMAC token issuer.

Thread-safety: each write appends a single JSONL row — safe under
concurrent writers on POSIX (single `write(2)` on a pipe-like log).
Reads always replay from the file.

## Methods

- [[core-security-identity-py-IdentityStore-__init__]]`() → None` — 
- [[core-security-identity-py-IdentityStore-_load_secret]]`() → bytes` — 
- [[core-security-identity-py-IdentityStore-create_user]]`(user_id, role) → tuple[User, str]` — Create a user. Returns (user, raw_api_key).
- [[core-security-identity-py-IdentityStore-assign_role]]`(user_id, role) → User` — Append a new record with the updated role. History preserved.
- [[core-security-identity-py-IdentityStore-disable_user]]`(user_id) → User` — 
- [[core-security-identity-py-IdentityStore-get_user]]`(user_id) → User | None` — 
- [[core-security-identity-py-IdentityStore-list_users]]`() → list[User]` — 
- [[core-security-identity-py-IdentityStore-authenticate]]`(user_id, api_key) → Token` — Verify credentials and return a signed token.
- [[core-security-identity-py-IdentityStore-verify]]`(token_str) → Token` — Parse + verify a token string. Raises AuthError on any failure.
- [[core-security-identity-py-IdentityStore-revoke]]`(jti) → None` — Revoke a token by its jti. Idempotent.
- [[core-security-identity-py-IdentityStore-_issue_token]]`(user) → Token` — 
- [[core-security-identity-py-IdentityStore-_append_user]]`(user) → None` — 
- [[core-security-identity-py-IdentityStore-_iter_rows]]`(path) → Iterable[dict]` — 
- [[core-security-identity-py-IdentityStore-_revoked_jtis]]`() → set[str]` — 
