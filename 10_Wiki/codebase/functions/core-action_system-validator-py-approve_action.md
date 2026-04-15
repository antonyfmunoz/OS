---
type: codebase-function
file: core/action_system/validator.py
line: 126
generated: 2026-04-12
---

# approve_action

**File:** [[core-action_system-validator-py]] | **Line:** 126
**Signature:** `approve_action(action) → dict[str, Any]`

Approve or defer an action based on its risk_level.

v1 policy:
  - low         → auto-approve
  - medium/high → require explicit_approval=True
...
