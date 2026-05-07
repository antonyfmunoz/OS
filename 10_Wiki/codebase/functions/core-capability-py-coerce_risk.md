---
type: codebase-function
file: core/capability.py
line: 144
generated: 2026-05-07
---

# coerce_risk

**File:** [[core-capability-py]] | **Line:** 144
**Signature:** `coerce_risk(value) → RiskTier`

Accept str or RiskTier, return RiskTier. Unknown → NONE.

## Called By

- [[core-advisor-py-needs_advisor]]
- [[core-capability-py-CapabilityEnforcer-may]]
- [[core-security-context-py-SecurityContext-authorize_action]]
- [[core-security-environments-py-SecurityEnv-blocks]]
- [[core-security-environments-py-SecurityEnv-needs_approval]]
- [[core-security-rbac-py-RBACEngine-can_approve]]
- [[core-security-rbac-py-RBACEngine-check]]
