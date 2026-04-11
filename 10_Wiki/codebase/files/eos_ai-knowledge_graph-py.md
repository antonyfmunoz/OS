---
type: codebase-file
path: eos_ai/knowledge_graph.py
module: eos_ai.knowledge_graph
lines: 530
size: 20822
generated: 2026-04-11
---

# eos_ai/knowledge_graph.py

KnowledgeGraph — entity relationship layer for EOS.

Connects leads, signals, conversations, outcomes, skills, ventures,
agents, and events into a navigable graph. Memory becomes a list only
without this; with it the system can reason about relationships.
...

**Lines:** 530 | **Size:** 20,822 bytes

## Depends On

- [[eos_ai-context-py]]
- [[eos_ai-db-py]]

## Used By

- [[eos_ai-onboarding_backfill-py]]

## Contains

- **class** [[eos_ai-knowledge_graph-py-KnowledgeGraph]] — 8 methods
- **fn** [[eos_ai-knowledge_graph-py-_utcnow]]`() → str`

## Import Statements

```python
import json
from datetime import datetime
from datetime import timezone
from eos_ai.context import EOSContext
from eos_ai.db import get_conn
from eos_ai.db import resolve_venture
from eos_ai.db import ORG_ID
```
