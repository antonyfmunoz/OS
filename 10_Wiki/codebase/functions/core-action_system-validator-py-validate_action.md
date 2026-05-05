---
type: codebase-function
file: core/action_system/validator.py
line: 59
generated: 2026-04-12
---

# validate_action

**File:** [[core-action_system-validator-py]] | **Line:** 59
**Signature:** `validate_action(action) → dict[str, Any]`

Return a dict describing validation outcome and mutate action.validation.

The Control Plane decides what to do with a failed validation; this
function only reports.

## Calls

- [[core-action_system-validator-py-_check_path_safety]]
- [[core-action_system-validator-py-_check_shell_safety]]
