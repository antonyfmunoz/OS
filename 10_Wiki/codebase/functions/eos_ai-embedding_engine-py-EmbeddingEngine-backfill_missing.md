---
type: codebase-function
file: eos_ai/embedding_engine.py
line: 339
generated: 2026-04-11
---

# EmbeddingEngine.backfill_missing

**File:** [[eos_ai-embedding_engine-py]] | **Line:** 339
**Signature:** `backfill_missing(org_id, limit) → dict`

**Class:** [[eos_ai-embedding_engine-py-EmbeddingEngine]]

Find interactions without embeddings and embed them in bulk.
Rate-limited: pauses 1s every 20 rows to avoid API limits.
Returns stats dict: found, embedded, failed, skipped.

## Calls

- [[eos_ai-embedding_engine-py-EmbeddingEngine-embed_interaction]]
- [[eos_ai-embedding_engine-py-EmbeddingEngine-is_available]]
