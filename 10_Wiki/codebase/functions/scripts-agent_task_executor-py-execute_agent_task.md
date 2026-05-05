---
type: codebase-function
file: scripts/agent_task_executor.py
line: 99
generated: 2026-04-12
---

# execute_agent_task

**File:** [[scripts-agent_task_executor-py]] | **Line:** 99
**Signature:** `execute_agent_task(task, ctx) → dict`

Execute a single agent task through the cognitive loop.
Returns a result dict with status, output, agent_id, display_name, tokens.

## Calls

- [[scripts-agent_task_executor-py-load_soul_doc]]

## Called By

- [[scripts-agent_task_executor-py-run_executor]]
