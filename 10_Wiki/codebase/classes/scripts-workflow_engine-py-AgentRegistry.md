---
type: codebase-class
file: scripts/workflow_engine.py
line: 214
generated: 2026-04-12
---

# AgentRegistry

**File:** [[scripts-workflow_engine-py]] | **Line:** 214

Lookup table + default roster.

Keep the roster small and explicit. Adding an agent = adding a role, not
a whim. Each agent here is a real capability boundary the executor trusts.

## Methods

- [[scripts-workflow_engine-py-AgentRegistry-__init__]]`() → None` — 
- [[scripts-workflow_engine-py-AgentRegistry-_register_defaults]]`() → None` — 
- [[scripts-workflow_engine-py-AgentRegistry-register]]`(agent) → None` — 
- [[scripts-workflow_engine-py-AgentRegistry-get]]`(name) → Agent` — 
- [[scripts-workflow_engine-py-AgentRegistry-names]]`() → list[str]` — 
