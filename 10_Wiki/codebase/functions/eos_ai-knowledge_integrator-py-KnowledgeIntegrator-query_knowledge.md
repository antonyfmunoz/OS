---
type: codebase-function
file: eos_ai/knowledge_integrator.py
line: 224
generated: 2026-04-12
---

# KnowledgeIntegrator.query_knowledge

**File:** [[eos_ai-knowledge_integrator-py]] | **Line:** 224
**Signature:** `query_knowledge(query, limit) → list[dict]`

**Class:** [[eos_ai-knowledge_integrator-py-KnowledgeIntegrator]]

Semantic search across all stored knowledge.
Returns top-N results by embedding similarity.
Degrades to empty list when embedding engine unavailable.

## Calls

- [[eos_ai-embedding_engine-py-EmbeddingEngine-is_available]]
- [[eos_ai-embedding_engine-py-EmbeddingEngine-semantic_search]]
- [[eos_ai-memory-py-AgentMemory-semantic_search]]

## Called By

- [[eos_ai-world_pulse-py-WorldPulse-get_pulse_summary]]
