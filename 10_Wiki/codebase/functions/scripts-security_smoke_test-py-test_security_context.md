---
type: codebase-function
file: scripts/security_smoke_test.py
line: 321
generated: 2026-04-12
---

# test_security_context

**File:** [[scripts-security_smoke_test-py]] | **Line:** 321
**Signature:** `test_security_context(tmp) → None`

*No docstring.*

## Calls

- [[core-security-approval-py-ApprovalQueue-approve]]
- [[core-security-audit-py-AuditLog-verify_chain]]
- [[core-security-context-py-SecurityContext-approve]]
- [[core-security-context-py-SecurityContext-authorize_action]]
- [[core-security-environments-py-env_for_name]]
- [[core-security-identity-py-IdentityStore-authenticate]]
- [[core-security-identity-py-IdentityStore-create_user]]
- [[scripts-security_smoke_test-py-assert_eq]]
- [[scripts-security_smoke_test-py-assert_true]]
- [[scripts-security_smoke_test-py-step]]

## Called By

- [[scripts-security_smoke_test-py-main]]
