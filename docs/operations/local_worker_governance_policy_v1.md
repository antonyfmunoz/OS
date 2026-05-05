# Local Worker Governance Policy v1

**Phase:** 96.8A
**Status:** Active
**Layer:** UMH Substrate — `core/environment_bridge/packet_validator.py`

## Purpose

Defines the governance rules that every work packet must satisfy
before the local worker is allowed to execute it. Governance is
enforced at the packet level, not the worker level.

## Validation Chain

The packet validator runs these checks in order. First failure
blocks execution:

```
1. packet_id present?           → MISSING_PACKET_ID
2. action_type present?         → UNKNOWN_ACTION_TYPE (blocks)
3. HIGH/CRITICAL + approved?    → MISSING_APPROVAL (blocks)
4. expires_at valid?            → EXPIRED (runtime check)
5. blocked_actions present?     → MISSING_GOVERNANCE (blocks)
6. CU governance (if GUI)?      → MISSING_GOVERNANCE (blocks)
7. proof_requirements present?  → MISSING_PROOF_REQUIREMENTS (blocks)
8. allowed/blocked overlap?     → UNSAFE_ACTION (blocks)
9. All checks pass              → VALID (can_execute = true)
```

## CU Required Blocked Actions

Any packet targeting `local_windows_gui` or `local_browser` must
block ALL of these actions:

| # | Action | Why |
|---|--------|-----|
| 1 | `credential_capture` | Never capture credentials |
| 2 | `token_capture` | Never capture tokens |
| 3 | `cookie_capture` | Never capture cookies |
| 4 | `account_switching` | Stay on approved account |
| 5 | `gmail` | No email access |
| 6 | `edit` | Read-only operations |
| 7 | `delete` | No deletions |
| 8 | `move` | No file moves |
| 9 | `share` | No sharing changes |
| 10 | `permission_change` | No permission changes |
| 11 | `export` | No exports |
| 12 | `download` | No downloads |
| 13 | `screenshot` | No screenshots |
| 14 | `ocr` | No OCR |
| 15 | `playwright` | No Playwright automation |
| 16 | `cdp` | No Chrome DevTools Protocol |
| 17 | `memory_promotion` | No memory promotion |

## Result Governance

Results are validated by `result_ingestion.py`:

1. `no_secret_confirmed` — worker confirms no secrets captured
2. `no_mutation_confirmed` — worker confirms no mutations performed
3. `governance_report` — per-check pass/fail dictionary
4. `proof_artifacts` — at least one proof artifact required

Priority: governance violations > proof incomplete > missing confirmations.

## Founder Confirmation

When `founder_confirmation_required` is true on a packet, the system
requires explicit founder input. The confirmation gate NEVER
auto-applies — it must come from the founder directly.
