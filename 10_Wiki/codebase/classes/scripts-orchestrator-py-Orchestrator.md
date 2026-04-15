---
type: codebase-class
file: scripts/orchestrator.py
line: 763
generated: 2026-04-12
---

# Orchestrator

**File:** [[scripts-orchestrator-py]] | **Line:** 763

Top-level coordinator. One per process.

Lifecycle:
    orch = Orchestrator()
    orch.register(job1); orch.register(job2)
...

## Methods

- [[scripts-orchestrator-py-Orchestrator-__init__]]`() → None` — 
- [[scripts-orchestrator-py-Orchestrator-register]]`(job) → None` — 
- [[scripts-orchestrator-py-Orchestrator-unregister]]`(job_id) → bool` — 
- [[scripts-orchestrator-py-Orchestrator-jobs]]`() → list[Job]` — 
- [[scripts-orchestrator-py-Orchestrator-submit]]`(job) → bool` — 
- [[scripts-orchestrator-py-Orchestrator-trigger]]`(job_id) → bool` — 
- [[scripts-orchestrator-py-Orchestrator-start]]`() → None` — 
- [[scripts-orchestrator-py-Orchestrator-stop]]`() → None` — 
- [[scripts-orchestrator-py-Orchestrator-wait]]`() → None` — Block until stop() is called. Intended for foreground `start`.
- [[scripts-orchestrator-py-Orchestrator-status]]`() → dict[str, Any]` — 
- [[scripts-orchestrator-py-Orchestrator-save_state]]`() → None` — 
