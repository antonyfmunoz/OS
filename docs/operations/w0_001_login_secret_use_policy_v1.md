# W0-001 Login Secret Use Policy v1

**Phase**: 94D.9S
**Work Order**: WO-LOCAL-PILOT-GDRIVE-GDOCS-001
**Target Account**: antonyfm@empyreanstudios.co
**Date**: 2026-05-04

---

## 1. Decision Tree

```
START
  │
  ├─ Step 1: Run Chrome Profile Resolver
  │    │
  │    ├─ PROFILE_MATCH_FOUND (Profile 5) → Launch with --profile-directory
  │    │    │
  │    │    ├─ Drive opens, correct account → PROCEED to next gate
  │    │    └─ Drive opens, LOGIN_REQUIRED → Step 2
  │    │
  │    ├─ NO_MATCH_FOUND → Founder decision (manual login / create profile)
  │    └─ MULTIPLE_MATCHES → Founder picks one
  │
  ├─ Step 2: Login Required Decision
  │    │
  │    ├─ Option A: MANUAL_LOGIN (default)
  │    │    Worker pauses. Founder logs in manually.
  │    │    Worker resumes at VERIFY_ACTIVE_GOOGLE_ACCOUNT.
  │    │
  │    └─ Option B: SECRET_ASSISTED_LOGIN (founder-enabled only)
  │         Worker requests SecretUseGrant.
  │         Founder approves.
  │         Worker uses secret broker.
  │         Value injected locally, never in model context.
  │         │
  │         ├─ Login succeeds → VERIFY_ACTIVE_GOOGLE_ACCOUNT
  │         └─ Login fails → report failure, do not retry with different creds
  │
  ├─ Step 3: 2FA Gate (if triggered)
  │    │
  │    └─ ALWAYS PAUSE for human intervention
  │         - No TOTP automation by default
  │         - No SMS interception
  │         - No push approval automation
  │         - Founder completes 2FA manually
  │
  └─ Step 4: VERIFY_ACTIVE_GOOGLE_ACCOUNT
       │
       ├─ CORRECT_ACCOUNT_CONFIRMED → STOP (do not continue to Drive discovery)
       ├─ WRONG_ACCOUNT → PAUSE (do not switch)
       └─ LOGIN_REQUIRED → back to Step 2
```

## 2. Secret Reference for W0-001

```
secret_ref: GOOGLE_ANTONYFM_PASSWORD
scope: google_workspace
account: antonyfm@empyreanstudios.co
backend: local_env
path: ~/.umh/secrets/.env
```

## 3. What Secret-Assisted Login Does

1. Reads password from local .env file
2. Types password into Chrome login form via local keyboard injection
3. Reports LOGIN_SUCCESS or LOGIN_FAILURE
4. Secret value is NEVER sent to VPS, model, logs, or messages

## 4. What Secret-Assisted Login Does NOT Do

- Does NOT capture or store the password after use
- Does NOT send the password over SSH
- Does NOT include the password in any message
- Does NOT remember the password in memory/wiki
- Does NOT automate 2FA
- Does NOT retry with alternative credentials
- Does NOT fall back to credential scraping

## 5. Approval Flow

```
Worker → "LOGIN_REQUIRED for antonyfm@empyreanstudios.co. Use secret-assisted login?"
Founder → "APPROVE" or "MANUAL_LOGIN" or "CANCEL"

If APPROVE:
  Worker → SecretUseRequest(key=GOOGLE_ANTONYFM_PASSWORD, action=LOGIN_GOOGLE_DRIVE)
  Founder → SecretUseGrant(approved_by=founder, single_use=true)
  Worker → [executes locally, reports result only]
```

## 6. After Login

STOP at VERIFY_ACTIVE_GOOGLE_ACCOUNT.
Do NOT proceed to:
- Drive file listing
- Document discovery
- Document reading
- Any ingestion

Until separately approved by a new gate.
