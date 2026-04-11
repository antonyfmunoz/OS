---
type: codebase-function
file: eos_ai/embedding_engine.py
line: 139
generated: 2026-04-11
---

# EmbeddingEngine.is_available

**File:** [[eos_ai-embedding_engine-py]] | **Line:** 139
**Signature:** `is_available() → bool`

**Class:** [[eos_ai-embedding_engine-py-EmbeddingEngine]]

True if ANY embedding method is functional (not just keyword fallback).

## Calls

- [[eos_ai-embedding_engine-py-EmbeddingEngine-_get_text_model]]

## Called By

- [[eos_ai-embedding_engine-py-EmbeddingEngine-backfill_missing]]
- [[eos_ai-knowledge_integrator-py-KnowledgeIntegrator-integrate]]
- [[eos_ai-knowledge_integrator-py-KnowledgeIntegrator-query_knowledge]]
