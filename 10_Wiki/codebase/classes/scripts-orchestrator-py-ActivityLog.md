---
type: codebase-class
file: scripts/orchestrator.py
line: 232
generated: 2026-04-12
---

# ActivityLog

**File:** [[scripts-orchestrator-py]] | **Line:** 232

Append-only JSONL log + best-effort AgentMemory mirror.

The JSONL file is authoritative. AgentMemory is a nice-to-have so the
cognition stack can semantic-search the orchestrator's history.

## Methods

- [[scripts-orchestrator-py-ActivityLog-__init__]]`(path) → None` — 
- [[scripts-orchestrator-py-ActivityLog-emit]]`(event) → None` — 
- [[scripts-orchestrator-py-ActivityLog-persist_to_memory]]`(job, result) → None` — Best-effort — never raises, never blocks the scheduler.
