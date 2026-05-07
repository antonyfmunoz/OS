---
type: codebase-function
file: eos_ai/memory.py
line: 558
generated: 2026-05-07
---

# AgentMemory.semantic_search

**File:** [[eos_ai-memory-py]] | **Line:** 558
**Signature:** `semantic_search(query, limit, min_similarity, venture_id) → list[dict]`

**Class:** [[eos_ai-memory-py-AgentMemory]]

Search past interactions by semantic similarity.
Uses cosine distance on 384-dim fastembed vectors.
Returns ranked results — most similar first.

## Calls

- [[eos_ai-db-py-get_conn]]
- [[eos_ai-db-py-resolve_venture]]

## Called By

- [[eos_ai-knowledge_integrator-py-KnowledgeIntegrator-query_knowledge]]
