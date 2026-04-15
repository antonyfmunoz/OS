---
type: codebase-function
file: core/action_system/policy.py
line: 79
generated: 2026-04-12
---

# normalize_risk

**File:** [[core-action_system-policy-py]] | **Line:** 79
**Signature:** `normalize_risk(value) → RiskLevel`

Coerce any caller-provided risk string into the canonical vocabulary.

Accepts both control-plane (`low`) and authority-engine (`LOW`)
forms. Unknown or empty → `low` (safest default for a runtime
action; callers that need strict validation use `validate_action`).

## Called By

- [[core-action_system-policy-py-blocks_auto_execute]]
- [[core-action_system-policy-py-map_to_authority_class]]
- [[core-action_system-policy-py-required_autonomy_level]]
- [[core-action_system-policy-py-requires_explicit_approval]]
- [[core-action_system-policy-py-resolve_effective_risk]]
