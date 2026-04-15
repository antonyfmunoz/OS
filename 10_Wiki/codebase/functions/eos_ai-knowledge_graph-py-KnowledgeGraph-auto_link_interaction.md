---
type: codebase-function
file: eos_ai/knowledge_graph.py
line: 464
generated: 2026-04-12
---

# KnowledgeGraph.auto_link_interaction

**File:** [[eos_ai-knowledge_graph-py]] | **Line:** 464
**Signature:** `auto_link_interaction(interaction_id) → None`

**Class:** [[eos_ai-knowledge_graph-py-KnowledgeGraph]]

Called after every interaction is logged.
Creates entity_links: interaction → venture, skill, agent, lead.

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-knowledge_graph-py-KnowledgeGraph-link_entities]]
