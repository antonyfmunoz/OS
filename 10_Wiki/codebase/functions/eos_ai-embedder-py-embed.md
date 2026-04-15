---
type: codebase-function
file: eos_ai/embedder.py
line: 40
generated: 2026-04-12
---

# embed

**File:** [[eos_ai-embedder-py]] | **Line:** 40
**Signature:** `embed(text) → np.ndarray`

Return a normalized 384-dim float32 embedding for text.
L2-normalized so dot product == cosine similarity.

## Calls

- [[eos_ai-embedder-py-_get_model]]
