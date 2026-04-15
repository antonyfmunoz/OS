---
type: codebase-class
file: eos_ai/knowledge_graph.py
line: 25
generated: 2026-04-12
---

# KnowledgeGraph

**File:** [[eos_ai-knowledge_graph-py]] | **Line:** 25

*No docstring.*

## Methods

- [[eos_ai-knowledge_graph-py-KnowledgeGraph-__init__]]`(ctx)` — 
- [[eos_ai-knowledge_graph-py-KnowledgeGraph-_ensure_table]]`() → None` — 
- [[eos_ai-knowledge_graph-py-KnowledgeGraph-link_entities]]`(from_type, from_id, to_type, to_id, relationship, metadata) → str` — Write a directed edge from_entity → to_entity.
- [[eos_ai-knowledge_graph-py-KnowledgeGraph-get_entity_context]]`(entity_type, entity_id, depth) → dict` — Traverse entity_links from this entity.
- [[eos_ai-knowledge_graph-py-KnowledgeGraph-_traverse]]`(entity_type, entity_id, remaining_depth, visited) → dict` — 
- [[eos_ai-knowledge_graph-py-KnowledgeGraph-get_lead_journey]]`(username) → dict` — Complete traversal for a lead. Finds all signals, conversations,
- [[eos_ai-knowledge_graph-py-KnowledgeGraph-find_patterns]]`(venture_id) → list[dict]` — Look for recurring patterns in interaction + outcome data.
- [[eos_ai-knowledge_graph-py-KnowledgeGraph-auto_link_interaction]]`(interaction_id) → None` — Called after every interaction is logged.
