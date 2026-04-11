---
type: codebase-function
file: eos_ai/embedding_engine.py
line: 258
generated: 2026-04-11
---

# EmbeddingEngine.semantic_search

**File:** [[eos_ai-embedding_engine-py]] | **Line:** 258
**Signature:** `semantic_search(query, org_id, limit, venture_id) → list[dict]`

**Class:** [[eos_ai-embedding_engine-py-EmbeddingEngine]]

Return the top-N interactions most semantically similar to query.

Falls back to recency-based search if all embedding tiers fail.

## Calls

- [[eos_ai-embedding_engine-py-EmbeddingEngine-_recent_fallback]]
- [[eos_ai-embedding_engine-py-EmbeddingEngine-embed]]

## Called By

- [[eos_ai-knowledge_integrator-py-KnowledgeIntegrator-query_knowledge]]
