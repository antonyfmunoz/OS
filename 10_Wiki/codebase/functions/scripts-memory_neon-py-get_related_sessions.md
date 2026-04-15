---
type: codebase-function
file: scripts/memory_neon.py
line: 384
generated: 2026-04-12
---

# get_related_sessions

**File:** [[scripts-memory_neon-py]] | **Line:** 384
**Signature:** `get_related_sessions(entity_id, entity_type, relationship, limit) → list[dict]`

Traverse entity_links to find related nodes.

Given an entity (e.g. a summary slug), find all connected entities
via entity_links. Works in both directions (from→to and to→from).

...

## Calls

- [[eos_ai-db-py-get_conn]]
