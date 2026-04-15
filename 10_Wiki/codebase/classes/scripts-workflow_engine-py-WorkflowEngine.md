---
type: codebase-class
file: scripts/workflow_engine.py
line: 710
generated: 2026-04-12
---

# WorkflowEngine

**File:** [[scripts-workflow_engine-py]] | **Line:** 710

Runs workflows end-to-end. One engine per process is enough.

Environment-aware: pass `env=make_sandbox(...)` to redirect log +
state writes and any downstream ActionSystem edits into an isolated
tree. Default is production.

## Methods

- [[scripts-workflow_engine-py-WorkflowEngine-__init__]]`() → None` — 
- [[scripts-workflow_engine-py-WorkflowEngine-run_workflow]]`(wf) → dict` — 
- [[scripts-workflow_engine-py-WorkflowEngine-_run_step_with_retry]]`(wf, step, context) → None` — 
- [[scripts-workflow_engine-py-WorkflowEngine-_aggregate]]`(wf) → dict` — 
- [[scripts-workflow_engine-py-WorkflowEngine-_emit]]`(event, wf) → None` — 
- [[scripts-workflow_engine-py-WorkflowEngine-_save_state]]`(wf) → None` — 
- [[scripts-workflow_engine-py-WorkflowEngine-_log_to_memory]]`(wf) → None` — Persist the final outcome to AgentMemory so future workflows can
- [[scripts-workflow_engine-py-WorkflowEngine-_finalize]]`(wf) → dict` — 
