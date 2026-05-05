---
type: codebase-function
file: eos_ai/memory.py
line: 547
generated: 2026-04-12
---

# AgentMemory.embed_and_store

**File:** [[eos_ai-memory-py]] | **Line:** 547
**Signature:** `embed_and_store(interaction_id, text) → bool`

**Class:** [[eos_ai-memory-py-AgentMemory]]

Embed text and persist the vector for interaction_id.

Delegates to EmbeddingEngine.embed_interaction() — the canonical
write path. Schema is vector(384); fastembed BAAI/bge-small-en-v1.5
produces matching 384-dim vectors. Returns True on success.
