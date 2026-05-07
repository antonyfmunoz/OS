---
type: codebase-function
file: eos_ai/embedding_engine.py
line: 161
generated: 2026-05-07
---

# EmbeddingEngine.embed_interaction

**File:** [[eos_ai-embedding_engine-py]] | **Line:** 161
**Signature:** `embed_interaction(interaction_id, content, org_id) → bool`

**Class:** [[eos_ai-embedding_engine-py-EmbeddingEngine]]

Embed content and store in the Neon embeddings table.
Called after every interaction is logged — never blocks the main call.
Deletes any existing embedding for this interaction before reinserting.
Records which model/tier was used in embedding_model column.

## Calls

- [[eos_ai-embedding_engine-py-EmbeddingEngine-_get_text_model]]
- [[eos_ai-embedding_engine-py-EmbeddingEngine-embed]]

## Called By

- [[eos_ai-embedding_engine-py-EmbeddingEngine-backfill_missing]]
- [[eos_ai-knowledge_integrator-py-KnowledgeIntegrator-integrate]]
