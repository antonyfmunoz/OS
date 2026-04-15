---
type: codebase-function
file: eos_ai/venture_knowledge.py
line: 257
generated: 2026-04-12
---

# VentureKnowledgeBase.get_ventures_from_db

**File:** [[eos_ai-venture_knowledge-py]] | **Line:** 257
**Signature:** `get_ventures_from_db(org_id) → dict`

**Class:** [[eos_ai-venture_knowledge-py-VentureKnowledgeBase]]

Query the ventures table for the given org_id and return a dict
matching the _ventures structure keyed by slug (name lowercased, spaces → _).

Called by to_agent_context() as fallthrough when venture_id is not in
the hardcoded _ventures dict. Returns {} on any DB error.

## Calls

- [[eos_ai-db-py-get_conn]]

## Called By

- [[eos_ai-venture_knowledge-py-VentureKnowledgeBase-to_agent_context]]

## Decorators

- `@classmethod`
