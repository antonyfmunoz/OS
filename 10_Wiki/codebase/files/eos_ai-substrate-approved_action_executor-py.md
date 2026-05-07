---
type: codebase-file
path: eos_ai/substrate/approved_action_executor.py
module: eos_ai.substrate.approved_action_executor
lines: 339
size: 10928
generated: 2026-05-07
---

# eos_ai/substrate/approved_action_executor.py

Approved action executor for Phase 94D.7R.

Validates advisor approval responses and dispatches only the single
named approved action. Rejects anything not explicitly approved.

...

**Lines:** 339 | **Size:** 10,928 bytes

## Contains

- **fn** [[eos_ai-substrate-approved_action_executor-py-_now_iso]]`() → str`
- **fn** [[eos_ai-substrate-approved_action_executor-py-normalize_decision]]`(decision) → str`
- **fn** [[eos_ai-substrate-approved_action_executor-py-extract_approved_action]]`(response) → str`
- **fn** [[eos_ai-substrate-approved_action_executor-py-extract_decision]]`(response) → str`
- **fn** [[eos_ai-substrate-approved_action_executor-py-extract_work_order_id]]`(response) → str`
- **fn** [[eos_ai-substrate-approved_action_executor-py-get_preferred_backend]]`(action) → str`
- **fn** [[eos_ai-substrate-approved_action_executor-py-validate_approval_for_action]]`(response, expected_action, expected_work_order_id) → list[str]`
- **fn** [[eos_ai-substrate-approved_action_executor-py-is_action_blocked]]`(action) → bool`
- **fn** [[eos_ai-substrate-approved_action_executor-py-is_action_supported]]`(action) → bool`
- **fn** [[eos_ai-substrate-approved_action_executor-py-build_action_executed_result]]`(work_order_id, action, backend, success, detail, target_account, chrome_path) → dict[str, Any]`
- **fn** [[eos_ai-substrate-approved_action_executor-py-build_backend_missing_result]]`(work_order_id, action, reason) → dict[str, Any]`
- **fn** [[eos_ai-substrate-approved_action_executor-py-build_next_gate_request]]`(work_order_id, gate_action, description, target_account, possible_states) → dict[str, Any]`
- **fn** [[eos_ai-substrate-approved_action_executor-py-build_login_required_gate]]`(work_order_id, target_account) → dict[str, Any]`
- **fn** [[eos_ai-substrate-approved_action_executor-py-execute_approved_action]]`(response, action, executor_fn, work_order_id) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import json
import time
from datetime import datetime
from datetime import timezone
from typing import Any
```
