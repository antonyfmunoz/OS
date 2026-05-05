---
type: codebase-function
file: eos_ai/db.py
line: 112
generated: 2026-04-12
---

# resolve_skill

**File:** [[eos_ai-db-py]] | **Line:** 112
**Signature:** `resolve_skill(name) → str | None`

Map a Python skill name to its Neon UUID.

Skill names match the 'name' column in the skills table exactly.
e.g. "analyze_icp_signal" → "<uuid>"

...

## Called By

- [[eos_ai-memory-py-AgentMemory-log]]
- [[eos_ai-memory-py-AgentMemory-log_lead_scored]]
