---
type: codebase-class
file: scripts/orchestrator.py
line: 600
generated: 2026-04-12
---

# EventAgent

**File:** [[scripts-orchestrator-py]] | **Line:** 600

Event-driven triggers.

Two event families:
  1. Filesystem changes — via watchdog. Jobs can register a glob pattern
     (e.g. "eos_ai/*.py"). The first match in a debounce window submits
...

## Methods

- [[scripts-orchestrator-py-EventAgent-__init__]]`(orchestrator) → None` — 
- [[scripts-orchestrator-py-EventAgent-start]]`() → None` — 
- [[scripts-orchestrator-py-EventAgent-stop]]`(timeout) → None` — 
- [[scripts-orchestrator-py-EventAgent-_make_handler]]`(base_cls) → Any` — 
- [[scripts-orchestrator-py-EventAgent-_dispatch_fs_event]]`(rel_path) → None` — 
- [[scripts-orchestrator-py-EventAgent-chain]]`(source_job_id, target_job_id) → None` — When source succeeds, submit target.
- [[scripts-orchestrator-py-EventAgent-_on_workflow_complete]]`(job, result) → None` — 
