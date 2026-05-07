---
type: codebase-function
file: eos_ai/substrate/computer_use_backend_contracts.py
line: 95
generated: 2026-05-07
---

# select_backend

**File:** [[eos_ai-substrate-computer_use_backend_contracts-py]] | **Line:** 95
**Signature:** `select_backend(task_type, work_order_id) → BackendPolicy`

Select execution backend for a work order task.

Rules:
- Founder override wins if provided
- Browser automation requires explicit approval
...
