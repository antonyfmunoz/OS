# Local .env Secret Backend Policy v1

**Phase**: 94D.9S
**Status**: ACTIVE
**Date**: 2026-05-04

---

## 1. Purpose

The local .env backend is the bootstrap/development secret store.
It allows the system to function before a production password manager
integration is implemented.

## 2. File Location

- Recommended: `~/.umh/secrets/.env`
- Alternative: any path OUTSIDE the repository
- NEVER inside `/opt/OS/` or any git-tracked directory

## 3. File Format

Standard .env format:
```
# Account secrets (EXAMPLE KEYS ONLY — NO VALUES IN THIS DOCUMENT)
GOOGLE_ANTONYFM_EMAIL=<value>
GOOGLE_ANTONYFM_PASSWORD=<value>
WHOP_EMAIL=<value>
WHOP_PASSWORD=<value>
```

## 4. Permissions

- File owner: root (or the user running the worker)
- File permissions: 600 (owner read/write only)
- Directory permissions: 700

```bash
mkdir -p ~/.umh/secrets
chmod 700 ~/.umh/secrets
touch ~/.umh/secrets/.env
chmod 600 ~/.umh/secrets/.env
```

## 5. What Is NOT Stored Here

- TOTP/2FA seeds (prefer manual 2FA by default)
- OAuth refresh tokens (managed by the application that created them)
- SSH private keys (already in ~/.ssh/)
- Session cookies (ephemeral, managed by Chrome)

## 6. Hard Rules

1. Never commit this file to git
2. Never copy it into the repository
3. Never copy it into documentation
4. Never send it to the VPS unless explicitly intended
5. Never include it in reports
6. Never ingest it into memory or wiki
7. Never read it into model context (load keys only, never values into prompts)
8. Never print its contents to stdout in full
9. Never include it in docker volumes
10. Never back it up to cloud storage without encryption

## 7. Validation

The backend validates:
- Path is outside repository root
- File exists and is readable
- Key format is valid (KEY=VALUE)

The backend rejects:
- Any path inside `/opt/OS/`
- Any path that resolves inside the repo via symlinks

## 8. Access Pattern

```python
# ALLOWED: Check if a key exists
keys = load_env_file_keys_only(path)

# ALLOWED: Check if specific secret is available
available = has_secret(path, "GOOGLE_ANTONYFM_PASSWORD")

# ALLOWED (inside approved action ONLY): Get value
status, value = get_secret_value_for_local_action(path, key)
# value MUST be used immediately and NEVER stored/logged/printed

# NEVER: Read file contents into model context
# NEVER: Print env file
# NEVER: Include value in any message
```

## 9. For W0-001

- Prefer Chrome profile/session routing first
- If login is required AND founder enables secret-assisted login:
  - secret_ref: `GOOGLE_ANTONYFM_PASSWORD`
  - scope: `google_workspace`
  - account: `antonyfm@empyreanstudios.co`
- Do NOT automate 2FA unless separately approved
- If 2FA appears, PAUSE for human intervention
