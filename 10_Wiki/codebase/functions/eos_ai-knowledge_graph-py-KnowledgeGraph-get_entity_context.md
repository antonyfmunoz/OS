---
type: codebase-function
file: eos_ai/knowledge_graph.py
line: 91
generated: 2026-05-07
---

# KnowledgeGraph.get_entity_context

**File:** [[eos_ai-knowledge_graph-py]] | **Line:** 91
**Signature:** `get_entity_context(entity_type, entity_id, depth) → dict`

**Class:** [[eos_ai-knowledge_graph-py-KnowledgeGraph]]

Traverse entity_links from this entity.
depth=1: direct connections only.
depth=2: connections of connections.
Returns: {entity: {type, id}, connections: [{relationship, direction, connected_entity}]}

## Calls

- [[eos_ai-knowledge_graph-py-KnowledgeGraph-_traverse]]
