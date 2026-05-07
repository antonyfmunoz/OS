---
type: codebase-function
file: eos_ai/embedder.py
line: 53
generated: 2026-05-07
---

# cosine_similarity

**File:** [[eos_ai-embedder-py]] | **Line:** 53
**Signature:** `cosine_similarity(a, b) → float`

Cosine similarity between two unit vectors.
Both inputs must be L2-normalized (use embed() to guarantee this).
Returns float in [-1, 1]; 1.0 = identical, 0.0 = orthogonal.
