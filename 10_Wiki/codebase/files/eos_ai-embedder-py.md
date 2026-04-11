---
type: codebase-file
path: eos_ai/embedder.py
module: eos_ai.embedder
lines: 70
size: 1997
generated: 2026-04-11
---

# eos_ai/embedder.py

Lightweight text embedder — shared singleton used by memory.py and
skill_registry.py.

Model: BAAI/bge-small-en-v1.5 via fastembed
  - 384-dimensional float32 vectors
...

**Lines:** 70 | **Size:** 1,997 bytes

## Contains

- **fn** [[eos_ai-embedder-py-_get_model]]`()`
- **fn** [[eos_ai-embedder-py-embed]]`(text) → np.ndarray`
- **fn** [[eos_ai-embedder-py-cosine_similarity]]`(a, b) → float`
- **fn** [[eos_ai-embedder-py-serialize]]`(vec) → bytes`
- **fn** [[eos_ai-embedder-py-deserialize]]`(blob) → np.ndarray`

## Import Statements

```python
import numpy as np
```
