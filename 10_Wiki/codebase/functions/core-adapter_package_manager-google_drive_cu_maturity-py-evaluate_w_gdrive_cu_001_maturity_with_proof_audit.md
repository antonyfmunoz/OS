---
type: codebase-function
file: core/adapter_package_manager/google_drive_cu_maturity.py
line: 262
generated: 2026-05-07
---

# evaluate_w_gdrive_cu_001_maturity_with_proof_audit

**File:** [[core-adapter_package_manager-google_drive_cu_maturity-py]] | **Line:** 262
**Signature:** `evaluate_w_gdrive_cu_001_maturity_with_proof_audit(proof, audit_result) → GoogleDriveCUMaturityDecision`

Evaluate maturity with proof audit gate.

If audit_result is provided and does not confirm auditable proof,
the decision status reflects provisional or needs-confirmation
even if all contract checks pass.

## Calls

- [[core-adapter_package_manager-google_drive_cu_maturity-py-evaluate_w_gdrive_cu_001_maturity]]
