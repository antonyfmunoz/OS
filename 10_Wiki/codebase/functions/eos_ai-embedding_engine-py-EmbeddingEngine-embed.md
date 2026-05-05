---
type: codebase-function
file: eos_ai/embedding_engine.py
line: 83
generated: 2026-04-12
---

# EmbeddingEngine.embed

**File:** [[eos_ai-embedding_engine-py]] | **Line:** 83
**Signature:** `embed(text, task_type) → Optional[list[float]]`

**Class:** [[eos_ai-embedding_engine-py-EmbeddingEngine]]

Generate an embedding vector using the first available tier.

Returns None only if all tiers fail — callers should fall back
to keyword-based search in that case.

...

## Calls

- [[eos_ai-embedding_engine-py-EmbeddingEngine-_get_text_model]]

## Called By

- [[eos_ai-embedding_engine-py-EmbeddingEngine-embed_interaction]]
- [[eos_ai-embedding_engine-py-EmbeddingEngine-semantic_search]]
