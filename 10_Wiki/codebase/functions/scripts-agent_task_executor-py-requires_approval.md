---
type: codebase-function
file: scripts/agent_task_executor.py
line: 164
generated: 2026-04-12
---

# requires_approval

**File:** [[scripts-agent_task_executor-py]] | **Line:** 164
**Signature:** `requires_approval(task, result) → bool`

Check whether the task description or result output contains signals
that indicate an external action requiring DEX approval before execution.

## Called By

- [[scripts-agent_task_executor-py-run_executor]]
