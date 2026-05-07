---
type: codebase-function
file: core/security/rbac.py
line: 221
generated: 2026-05-07
---

# RBACEngine.check

**File:** [[core-security-rbac-py]] | **Line:** 221
**Signature:** `check(role_name, op, risk) → RBACCheck`

**Class:** [[core-security-rbac-py-RBACEngine]]

Evaluate whether `role_name` may request `op` at `risk`.

Returns RBACCheck. Never raises; callers decide what to do.

## Calls

- [[core-capability-py-cap_implies]]
- [[core-capability-py-coerce_risk]]
- [[core-capability-py-required_capability]]
- [[core-security-rbac-py-RBACEngine-get]]

## Called By

- [[scripts-security_smoke_test-py-test_rbac]]
