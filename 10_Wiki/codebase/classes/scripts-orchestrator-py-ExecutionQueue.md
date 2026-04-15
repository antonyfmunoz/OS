---
type: codebase-class
file: scripts/orchestrator.py
line: 300
generated: 2026-04-12
---

# ExecutionQueue

**File:** [[scripts-orchestrator-py]] | **Line:** 300

Bounded queue + thread pool that actually runs workflows.

* Max queue depth bounds backpressure — submit() raises Full rather than
  growing memory forever.
* max_concurrent bounds how many workflows can run simultaneously.
...

## Methods

- [[scripts-orchestrator-py-ExecutionQueue-__init__]]`() → None` — 
- [[scripts-orchestrator-py-ExecutionQueue-start]]`() → None` — 
- [[scripts-orchestrator-py-ExecutionQueue-stop]]`() → None` — 
- [[scripts-orchestrator-py-ExecutionQueue-submit]]`(job) → bool` — Enqueue a job run. Returns True if accepted, False otherwise.
- [[scripts-orchestrator-py-ExecutionQueue-on_complete]]`(handler) → None` — Register a callback fired after every run (success OR failure).
- [[scripts-orchestrator-py-ExecutionQueue-_dispatch_loop]]`() → None` — 
- [[scripts-orchestrator-py-ExecutionQueue-_run_job]]`(job, meta) → None` — 
- [[scripts-orchestrator-py-ExecutionQueue-depth]]`() → int` — 
- [[scripts-orchestrator-py-ExecutionQueue-active_keys]]`() → set[str]` — 
