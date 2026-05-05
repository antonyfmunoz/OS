# Secret Broker Doctrine v1

**Phase**: 94D.9S
**Status**: ACTIVE
**Date**: 2026-05-04

---

## 1. What Is a Secret

A secret is a **protected resource**. It is not memory. It is not data to be
processed. It is not content to be summarized. It is a value that exists solely
to be consumed by approved deterministic actions at execution time.

Secrets include:
- Passwords
- API keys
- Tokens (access, refresh, bearer)
- TOTP/2FA seeds
- Session cookies
- OAuth client secrets
- Private keys
- Connection strings containing credentials

## 2. What the Model May Know

The advisor/model may know:
- A secret reference exists (e.g., "there is a Google Workspace password for this account")
- What account/scope it belongs to
- Whether it is available in the configured backend
- What action it is approved for
- Whether use succeeded or failed

## 3. What the Model May NOT Know

The advisor/model may never know:
- The secret value itself
- Password text
- Token value
- Cookie/session value
- API key value
- 2FA code value
- Any string that would allow credential replay

## 4. Secret Use Flow

```
1. Worker reaches LOGIN_REQUIRED gate.
2. Worker asks advisor for permission to use a named secret_ref.
3. Human founder approves or denies.
4. Worker calls secret broker with the approved grant.
5. Secret broker injects value ONLY into the approved local action.
6. Secret value is redacted from ALL outputs/logs/messages.
7. Worker reports ONLY success/failure — never the secret.
```

## 5. Secret Lifecycle

```
CREATE  → founder places secret in backend (local .env, password manager)
EXIST   → broker reports key exists, never value
REQUEST → worker asks to use secret for specific action
APPROVE → founder grants single-use permission
USE     → broker injects into local action only
AUDIT   → use event logged (who, what, when — never value)
ROTATE  → founder updates value in backend
REVOKE  → founder removes secret from backend
```

## 6. Architecture Principle

Secrets are like file descriptors in an operating system:
- User-space (the model) gets an opaque handle (SecretRef)
- Kernel-space (the broker) does the actual I/O
- The handle can be passed around, inspected for metadata, checked for availability
- But the actual bytes never cross the user-space boundary

## 7. Non-Negotiable Rules

1. Secret values never appear in model context
2. Secret values never appear in logs
3. Secret values never appear in messages (inbox/outbox)
4. Secret values never appear in reports or documentation
5. Secret values never appear in exception traces
6. Secret values never appear in memory/wiki
7. Secret values never appear in screenshots
8. Secret values are never sent over chat interfaces
9. Secret values are never summarized or described
10. Secret values are never used for training

## 8. Governance Integration

Secret use is governed by the same gate system as all other actions:
- `capture_credentials` remains ALWAYS_BLOCKED
- Secret-assisted login is a new approved action type: `USE_SECRET_FOR_LOGIN`
- Requires explicit founder approval per use
- Single-use grants by default
- Audit trail maintained

## 9. Backends

The secret broker is backend-agnostic. Current:
- Local .env file (bootstrap/development)

Future:
- Windows Credential Manager
- 1Password CLI
- Bitwarden CLI
- Doppler / Infisical / Vault

All backends expose the same interface. Backend selection does not change
the non-exposure guarantees.
