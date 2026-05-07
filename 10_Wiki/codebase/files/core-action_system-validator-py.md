---
type: codebase-file
path: core/action_system/validator.py
module: core.action_system.validator
lines: 188
size: 6123
generated: 2026-05-07
---

# core/action_system/validator.py

Validation + approval rules for Actions.

Kept deliberately simple. Two concerns:
    1. Is the action well-formed and safe to consider? (validate_action)
    2. Should we run it right now?                     (approve_action)

**Lines:** 188 | **Size:** 6,123 bytes

## Contains

- **fn** [[core-action_system-validator-py-_check_path_safety]]`(path) → str | None`
- **fn** [[core-action_system-validator-py-_check_shell_safety]]`(command) → str | None`
- **fn** [[core-action_system-validator-py-validate_action]]`(action) → dict[str, Any]`
- **fn** [[core-action_system-validator-py-approve_action]]`(action) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
from typing import Any
from actions import Action
from actions import ALLOWED_ACTION_TYPES
from policy import blocks_auto_execute
from policy import normalize_risk
from policy import requires_explicit_approval
```
