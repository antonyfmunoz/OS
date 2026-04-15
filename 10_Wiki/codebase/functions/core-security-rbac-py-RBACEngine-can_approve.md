---
type: codebase-function
file: core/security/rbac.py
line: 281
generated: 2026-04-12
---

# RBACEngine.can_approve

**File:** [[core-security-rbac-py]] | **Line:** 281
**Signature:** `can_approve(role_name, risk) → bool`

**Class:** [[core-security-rbac-py-RBACEngine]]

True if this role's approval authority covers `risk`.

## Calls

- [[core-capability-py-coerce_risk]]
- [[core-security-rbac-py-RBACEngine-get]]

## Called By

- [[scripts-security_smoke_test-py-test_rbac]]
