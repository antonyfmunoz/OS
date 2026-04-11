---
type: codebase-function
file: core/action_system/policy.py
line: 133
generated: 2026-04-11
---

# resolve_effective_risk

**File:** [[core-action_system-policy-py]] | **Line:** 133
**Signature:** `resolve_effective_risk(declared_risk, business_action_type) → RiskLevel`

Return the stricter of the declared Control Plane risk and any
business-layer classification.

Rationale: a runtime action (e.g. `run_script`) that *also* represents
a business action (e.g. `publish_content`) should never execute at a
...

## Calls

- [[core-action_system-policy-py-authority_classify]]
- [[core-action_system-policy-py-normalize_risk]]
