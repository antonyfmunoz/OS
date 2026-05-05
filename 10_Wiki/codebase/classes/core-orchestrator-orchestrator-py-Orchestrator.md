---
type: codebase-class
file: core/orchestrator/orchestrator.py
line: 55
generated: 2026-04-12
---

# Orchestrator

**File:** [[core-orchestrator-orchestrator-py]] | **Line:** 55

*No docstring.*

## Methods

- [[core-orchestrator-orchestrator-py-Orchestrator-register_workflow]]`(name, workflow) → None` — 
- [[core-orchestrator-orchestrator-py-Orchestrator-list_workflows]]`() → list[str]` — 
- [[core-orchestrator-orchestrator-py-Orchestrator-run_workflow]]`(name, context) → dict[str, Any]` — Run a registered workflow by name.
- [[core-orchestrator-orchestrator-py-Orchestrator-_record_run]]`(name) → None` — 
- [[core-orchestrator-orchestrator-py-Orchestrator-_persist_unlocked]]`() → None` — 
- [[core-orchestrator-orchestrator-py-Orchestrator-load_state]]`() → None` — 
- [[core-orchestrator-orchestrator-py-Orchestrator-get_record]]`(name) → WorkflowRecord | None` — 

## Decorators

- `@dataclass`
