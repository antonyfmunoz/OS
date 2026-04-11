---
type: codebase-file
path: eos_ai/knowledge_integrator.py
module: eos_ai.knowledge_integrator
lines: 241
size: 7905
generated: 2026-04-11
---

# eos_ai/knowledge_integrator.py

KnowledgeIntegrator — permanent knowledge accumulation layer.

Every piece of information the system produces — web searches, market scans,
conversations, outcomes, world events, creator content — gets permanently
integrated into the knowledge base. Nothing is ever discarded.
...

**Lines:** 241 | **Size:** 7,905 bytes

## Depends On

- [[eos_ai-context-py]]
- [[eos_ai-embedding_engine-py]]
- [[eos_ai-memory-py]]

## Used By

- [[eos_ai-world_pulse-py]]
- [[services-discord_bot-py]]

## Contains

- **class** [[eos_ai-knowledge_integrator-py-KnowledgeIntegrator]] — 6 methods

## Import Statements

```python
import uuid
from typing import Optional
from eos_ai.context import EOSContext
from eos_ai.memory import AgentMemory
from eos_ai.embedding_engine import EmbeddingEngine
```
