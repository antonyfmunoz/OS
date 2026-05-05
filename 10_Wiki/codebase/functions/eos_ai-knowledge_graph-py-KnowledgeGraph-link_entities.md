---
type: codebase-function
file: eos_ai/knowledge_graph.py
line: 57
generated: 2026-04-12
---

# KnowledgeGraph.link_entities

**File:** [[eos_ai-knowledge_graph-py]] | **Line:** 57
**Signature:** `link_entities(from_type, from_id, to_type, to_id, relationship, metadata) → str`

**Class:** [[eos_ai-knowledge_graph-py-KnowledgeGraph]]

Write a directed edge from_entity → to_entity.
Returns the new link id (UUID string).

## Calls

- [[eos_ai-db-py-get_conn]]

## Called By

- [[eos_ai-knowledge_graph-py-KnowledgeGraph-auto_link_interaction]]
- [[eos_ai-onboarding_backfill-py-OnboardingBackfill-_backfill_drive]]
- [[eos_ai-onboarding_backfill-py-OnboardingBackfill-_backfill_gmail]]
