# CU Maturity Requires Auditable Proof v1

## Doctrine

Computer Use maturity requires auditable proof of actual GUI execution
or an explicitly accepted founder confirmation gate. Static contracts
and unit tests are not sufficient for final 100% maturity.

## Why

CU operates through a local visible GUI (Windows desktop, Chrome browser).
The VPS orchestrator drives execution remotely via Task Scheduler /IT
and SSH, but has no independent way to verify what appeared on the screen.
Unit tests validate contract logic — they do not prove the GUI rendered,
the account was correct, or the extraction actually ran.

## What Constitutes Auditable Proof

1. **Evidence data file** — structured JSON output from the CU execution
   (e.g., visible_drive_inventory.json) containing:
   - Method: COMPUTER_USE_ONLY
   - Backend: task_scheduler_it + ui_automation
   - Account: verified email
   - Items: actual extracted inventory
   - Governance flags: api_used=False, playwright_used=False, etc.

2. **Comparison data** — CU results matched against API baseline
   with recall, precision, and matching counts.

3. **Phase report** — docs/system/ report documenting execution path,
   constraints enforced, and results.

4. **Founder visual confirmation** (when required) — founder was present
   during execution or re-ran and confirmed output.

## What Does NOT Constitute Auditable Proof

- Unit tests that only check contract logic
- Hardcoded proof objects in Python code
- Self-reported maturity from the maturity evaluator
- Prior phase reports without corresponding data files
- Evidence from a different account or environment

## When Founder Confirmation Is Required

When all of the following are true:
- CU executed through a visible GUI on a remote machine
- The orchestrator drove execution via SSH/Task Scheduler
- The founder was not physically present during execution
- No independent verification mechanism exists

## Maturity Levels

| Proof Status | Maturity Allowed |
|-------------|-----------------|
| AUDITABLE_PROOF_CONFIRMED | 100% final |
| FOUNDER_CONFIRMATION_REQUIRED | provisional 100% pending confirmation |
| PROVISIONAL_PROOF | provisional, not final |
| INSUFFICIENT_PROOF | cannot claim any maturity |
| SYNTHETIC_ONLY | 0% — no evidence exists |
| STALE_PROOF | requires re-execution |

## Code Reference

- Audit: core/adapter_package_manager/cu_proof_audit.py
- Gate: core/adapter_package_manager/cu_founder_confirmation_gate.py
- Integration: evaluate_w_gdrive_cu_001_maturity_with_proof_audit()
