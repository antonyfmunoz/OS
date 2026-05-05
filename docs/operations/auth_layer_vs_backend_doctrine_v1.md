# Auth Layer vs Backend — Doctrine v1
**Phase**: 96.3/96.4  
**Status**: ACTIVE  
**Date**: 2026-05-04
---

## Core Rule
Authentication/authorization is a separate layer from backend selection. OAuth is an authorization mechanism, not a backend. Browser profile sessions are auth contexts, not backends. Secret values never enter model context.

## Details
### Separation Principle
- Auth profile is selected before or alongside backend — never after
- A single auth profile may serve multiple backends (e.g., one OAuth token used by API, SDK, and MCP)
- A single backend may support multiple auth methods (e.g., API key or OAuth)
- Auth layer handles token acquisition, refresh, and storage
- Backend layer handles extraction logic only

### 16 Auth Method Types
1. API_KEY — static secret, header or query param
2. OAUTH2_AUTH_CODE — full OAuth 2.0 authorization code flow
3. OAUTH2_CLIENT_CREDENTIALS — machine-to-machine OAuth
4. OAUTH2_DEVICE_CODE — device authorization grant
5. SERVICE_ACCOUNT — GCP/AWS service account JSON key
6. SESSION_COOKIE — browser session persistence
7. BROWSER_PROFILE — Chrome/Firefox profile with saved state
8. JWT_BEARER — signed JWT token
9. BASIC_AUTH — username:password base64
10. SAML — enterprise SSO assertion
11. PASSKEY — WebAuthn/FIDO2
12. MFA_TOTP — time-based one-time password
13. SSH_KEY — key-based shell authentication
14. CERTIFICATE — mTLS client certificate
15. ENVIRONMENT_VAR — secret loaded from .env at runtime
16. MANUAL — human enters credentials at execution time

### 7 Material Handling Levels
1. **NEVER_EXPOSED** — secret never leaves secure storage (hardware keys, passkeys)
2. **RUNTIME_ONLY** — loaded from .env, held in memory, never logged or transmitted to model
3. **ENCRYPTED_AT_REST** — stored encrypted, decrypted only at use time
4. **SCOPED_TOKEN** — short-lived, limited-permission derivative of a primary secret
5. **SESSION_BOUND** — valid only within a browser/process session
6. **LOGGED_HASH** — hash recorded for audit, plaintext never stored
7. **EXPOSED_TO_MODEL** — PROHIBITED; no secret value may reach model context

## Constraints
- Secret values MUST NOT enter model context under any circumstance
- Auth method selection MUST be independent of backend selection
- Token refresh logic MUST NOT live inside backend extraction code
- Browser profile sessions MUST NOT be classified as backends
- OAuth flows MUST NOT be described as "the OAuth backend"
- All auth methods MUST have a material handling level assigned
- EXPOSED_TO_MODEL is listed only to explicitly prohibit it — never assigned

## References
- `docs/operations/backend_registry_selection_doctrine_v1.md` — backend categories
- `docs/operations/non_exposure_credential_use_policy_v1.md` — credential handling
- `docs/operations/secret_broker_doctrine_v1.md` — secret management
