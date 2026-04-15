---
type: codebase-file
path: eos_ai/embedding_engine.py
module: eos_ai.embedding_engine
lines: 416
size: 15339
generated: 2026-04-12
---

# eos_ai/embedding_engine.py

EmbeddingEngine — Three-tier hybrid embedding with graceful degradation.

Tier 1: fastembed BAAI/bge-small-en-v1.5 (local, free, 384-dim) — primary.
         Matches the embeddings.embedding vector(384) schema exactly.
Tier 2: Gemini text-embedding (cloud, 768-dim) — fallback. NOTE: its 768-dim
...

**Lines:** 416 | **Size:** 15,339 bytes

## Used By

- [[eos_ai-knowledge_integrator-py]]
- [[eos_ai-onboarding_backfill-py]]

## Contains

- **class** [[eos_ai-embedding_engine-py-EmbeddingEngine]] — 9 methods

## Import Statements

```python
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
```
