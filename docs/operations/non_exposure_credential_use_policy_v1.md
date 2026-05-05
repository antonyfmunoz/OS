# Non-Exposure Credential Use Policy v1

**Phase**: 94D.9S
**Status**: ACTIVE
**Date**: 2026-05-04

---

## 1. Core Principle

The system may USE secrets. The model must NOT SEE secrets.

Secrets are opaque resources consumed by deterministic actions.
They are never part of reasoning, planning, summarization, or memory.

## 2. NEVER Do (Hard Rules)

| Action | Status |
|--------|--------|
| Echo/print secret values | BLOCKED |
| Write secret values to outbox/inbox messages | BLOCKED |
| Include secret values in JSON messages | BLOCKED |
| Include secret values in exception traces | BLOCKED |
| Print environment variables wholesale (`env`, `set`, `printenv`) | BLOCKED |
| Screenshot credential entry fields (unless separately approved + redacted) | BLOCKED |
| Store secret values in memory/wiki | BLOCKED |
| Promote secrets to any persistent store | BLOCKED |
| Train/fine-tune on secrets | BLOCKED |
| Summarize or describe secret values | BLOCKED |
| Include secrets in git commits | BLOCKED |
| Send secrets over chat (Discord, Slack, etc.) | BLOCKED |
| Include secrets in logs (stdout, stderr, file logs) | BLOCKED |
| Include secrets in model prompts or context | BLOCKED |
| Compare/diff secret values in observable output | BLOCKED |
| Use `cat`, `less`, `more` on secret files in model context | BLOCKED |

## 3. ALLOWED Actions

| Action | Status |
|--------|--------|
| Check whether a secret key exists | ALLOWED |
| Retrieve secret value inside local-only deterministic action | ALLOWED |
| Redact secret-like strings in all outputs | ALLOWED |
| Report success/failure of secret-assisted actions | ALLOWED |
| Build SecretRef metadata (key, scope, availability) | ALLOWED |
| Audit who used what secret, when (without value) | ALLOWED |
| Request permission to use a named secret | ALLOWED |
| Inject secret into stdin/clipboard of local action | ALLOWED (with grant) |

## 4. Redaction Requirements

All output channels must pass through redaction before being observable:
- Log output → `redact_potential_secrets_in_output()`
- Message payloads → `redact_mapping()` with known secret keys
- Exception handlers → catch and redact before re-raising
- Command output → `redact_secret_values()` with known values

## 5. Secret-Assisted Login Flow

```
1. Profile resolver finds correct Chrome profile
2. Chrome launched with --profile-directory
3. IF login required:
   a. Worker detects LOGIN_REQUIRED state
   b. Worker asks founder: "Use secret-assisted login?"
   c. Founder approves or chooses manual login
   d. IF approved:
      - Worker builds SecretUseRequest
      - Founder grants SecretUseGrant
      - Worker calls broker → gets value (internal only)
      - Worker injects value into local keyboard/form action
      - Value NEVER enters model context
      - Worker reports only: LOGIN_SUCCESS or LOGIN_FAILURE
   e. IF manual:
      - Worker pauses
      - Founder logs in manually
      - Worker resumes at VERIFY_ACTIVE_GOOGLE_ACCOUNT gate
4. After login:
   - VERIFY_ACTIVE_GOOGLE_ACCOUNT gate
   - Do NOT continue Drive discovery until separately approved
```

## 6. 2FA Policy

- 2FA automation is NOT enabled by default
- If 2FA prompt appears: PAUSE for human intervention
- Founder may later choose to enable TOTP automation (separate approval)
- SMS/push 2FA is always human-only
- 2FA codes are secrets and follow all the same non-exposure rules

## 7. Incident Response

If a secret value is accidentally exposed (in logs, messages, or model context):
1. Immediately rotate the secret
2. Purge the exposure from all logs/records
3. Document the incident (without the value)
4. Add a rule to prevent recurrence
5. Notify the founder
