# W0-001 Login-Safe Account Gate v1

**Phase**: 94D.7R
**Status**: PENDING — AWAITING VISUAL CONFIRMATION
**Date**: 2026-05-04

---

## Gate Request

```json
{
  "message_type": "APPROVAL_NEEDED",
  "work_order_id": "WO-LOCAL-PILOT-GDRIVE-GDOCS-001",
  "payload": {
    "approval_request_id": "apr_next_gate_1777931863",
    "action": "VERIFY_ACTIVE_GOOGLE_ACCOUNT",
    "target": "antonyfm@empyreanstudios.co",
    "description": "Verify active Google account is antonyfm@empyreanstudios.co. Visual confirmation required — is the correct account active in Chrome? If login required, respond LOGIN_REQUIRED_MANUAL_INTERVENTION. If wrong account, respond WRONG_ACCOUNT_PAUSE.",
    "risk_level": "LOW",
    "backend": "HUMAN_VISUAL_CONFIRMATION",
    "blocked_until_approved": true,
    "possible_states": [
      "DRIVE_OPEN_ACCOUNT_VISIBLE",
      "LOGIN_REQUIRED_MANUAL_INTERVENTION",
      "WRONG_ACCOUNT_PAUSE",
      "CORRECT_ACCOUNT_CONFIRMED",
      "UNKNOWN_VISUAL_STATE"
    ]
  }
}
```

## Possible States

### DRIVE_OPEN_ACCOUNT_VISIBLE
Chrome shows Google Drive with an account avatar/email visible.
Proceed to confirm which account is active.

### LOGIN_REQUIRED_MANUAL_INTERVENTION
Chrome shows Google Drive login page. Login is required.

Rules:
1. Emit LOGIN_REQUIRED_MANUAL_INTERVENTION to advisor.
2. Pause worker.
3. Ask founder to log in manually on the local PC.
4. Do NOT observe, capture, store, type, summarize, screenshot, or infer credentials.
5. After founder confirms login complete through advisor, proceed only to account verification.
6. Do NOT continue into Drive discovery until separately approved.

### WRONG_ACCOUNT_PAUSE
Chrome shows Google Drive logged into a different account.

Rules:
1. Emit WRONG_ACCOUNT_PAUSE.
2. Do NOT switch accounts automatically.
3. Ask advisor/founder for next instruction.
4. Do NOT access Drive content of the wrong account.

### CORRECT_ACCOUNT_CONFIRMED
Chrome shows Google Drive logged into `antonyfm@empyreanstudios.co`.

Rules:
1. Emit CORRECT_ACCOUNT_CONFIRMED.
2. Stop at READY_FOR_DRIVE_DISCOVERY_APPROVAL.
3. Do NOT open folders/docs yet.
4. Do NOT continue until separately approved.

### UNKNOWN_VISUAL_STATE
Cannot determine state. Ask for human clarification.

## Credential Safety Rules

The worker MUST NEVER:
- Type credentials, passwords, or 2FA codes
- Capture or store credentials in any form
- Screenshot login pages
- Read or parse login form content
- Infer credentials from URL parameters
- Store session tokens, cookies, or API keys
- Observe the login process

## How to Respond

If correct account active:
```json
{
  "work_order_id": "WO-LOCAL-PILOT-GDRIVE-GDOCS-001",
  "payload": {
    "decision": "APPROVE",
    "state": "CORRECT_ACCOUNT_CONFIRMED"
  }
}
```

If login required:
```json
{
  "work_order_id": "WO-LOCAL-PILOT-GDRIVE-GDOCS-001",
  "payload": {
    "decision": "PAUSE",
    "state": "LOGIN_REQUIRED_MANUAL_INTERVENTION",
    "instruction": "Please log in manually. Confirm when done."
  }
}
```

If wrong account:
```json
{
  "work_order_id": "WO-LOCAL-PILOT-GDRIVE-GDOCS-001",
  "payload": {
    "decision": "PAUSE",
    "state": "WRONG_ACCOUNT_PAUSE",
    "instruction": "Wrong account active. Manual switch needed."
  }
}
```
