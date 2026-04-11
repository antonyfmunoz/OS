---
type: codebase-function
file: core/action_system/policy.py
line: 114
generated: 2026-04-11
---

# authority_classify

**File:** [[core-action_system-policy-py]] | **Line:** 114
**Signature:** `authority_classify(business_action_type) → Optional[RiskLevel]`

Lazy, failure-tolerant lookup into `authority_engine.RISK_CLASSES`.

Returns the canonical Control Plane risk for a business action type
(`send_dm`, `publish_content`, ...) if the authority engine is
importable and knows about it. Returns None on any failure — the
...

## Called By

- [[core-action_system-policy-py-resolve_effective_risk]]
