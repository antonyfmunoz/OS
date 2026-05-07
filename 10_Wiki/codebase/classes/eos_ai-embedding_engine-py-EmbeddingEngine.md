---
type: codebase-class
file: eos_ai/embedding_engine.py
line: 29
generated: 2026-05-07
---

# EmbeddingEngine

**File:** [[eos_ai-embedding_engine-py]] | **Line:** 29

*No docstring.*

## Methods

- [[eos_ai-embedding_engine-py-EmbeddingEngine-__init__]]`()` — 
- [[eos_ai-embedding_engine-py-EmbeddingEngine-_get_text_model]]`()` — Lazy-load fastembed TextEmbedding model (cached after first call).
- [[eos_ai-embedding_engine-py-EmbeddingEngine-embed]]`(text, task_type) → Optional[list[float]]` — Generate an embedding vector using the first available tier.
- [[eos_ai-embedding_engine-py-EmbeddingEngine-is_available]]`() → bool` — True if ANY embedding method is functional (not just keyword fallback).
- [[eos_ai-embedding_engine-py-EmbeddingEngine-get_active_tier]]`() → str` — Return the highest-priority tier currently available. Used for monitoring.
- [[eos_ai-embedding_engine-py-EmbeddingEngine-embed_interaction]]`(interaction_id, content, org_id) → bool` — Embed content and store in the Neon embeddings table.
- [[eos_ai-embedding_engine-py-EmbeddingEngine-semantic_search]]`(query, org_id, limit, venture_id) → list[dict]` — Return the top-N interactions most semantically similar to query.
- [[eos_ai-embedding_engine-py-EmbeddingEngine-backfill_missing]]`(org_id, limit) → dict` — Find interactions without embeddings and embed them in bulk.
- [[eos_ai-embedding_engine-py-EmbeddingEngine-_recent_fallback]]`(org_id, limit, venture_id) → list[dict]` — Recency-based fallback when all embedding tiers fail.
