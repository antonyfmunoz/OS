---
type: codebase-function
file: core/capability.py
line: 59
generated: 2026-04-12
---

# cap_implies

**File:** [[core-capability-py]] | **Line:** 59
**Signature:** `cap_implies(have, need) → bool`

A higher-rank capability implies all lower ones.

## Called By

- [[core-capability-py-CapabilityEnforcer-may]]
- [[core-security-rbac-py-RBACEngine-check]]
