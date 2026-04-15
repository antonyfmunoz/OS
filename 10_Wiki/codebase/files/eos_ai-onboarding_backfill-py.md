---
type: codebase-file
path: eos_ai/onboarding_backfill.py
module: eos_ai.onboarding_backfill
lines: 339
size: 13497
generated: 2026-04-12
---

# eos_ai/onboarding_backfill.py

OnboardingBackfill — reads all connected integrations on first connect and
builds a complete knowledge base before the first interaction.

When a user connects their Google Workspace, this runs automatically and
populates: Drive docs, Gmail contacts, Calendar patterns, Google Tasks,
...

**Lines:** 339 | **Size:** 13,497 bytes

## Depends On

- [[eos_ai-cognitive_loop-py]]
- [[eos_ai-context-py]]
- [[eos_ai-embedding_engine-py]]
- [[eos_ai-gws_connector-py]]
- [[eos_ai-human_intelligence-py]]
- [[eos_ai-knowledge_graph-py]]

## Contains

- **class** [[eos_ai-onboarding_backfill-py-OnboardingBackfill]] — 9 methods

## Import Statements

```python
import re
from datetime import datetime
from datetime import timezone
from datetime import timedelta
from eos_ai.context import EOSContext
from eos_ai.gws_connector import GWSConnector
from eos_ai.cognitive_loop import CognitiveLoop
from eos_ai.human_intelligence import HumanIntelligenceEngine
from eos_ai.knowledge_graph import KnowledgeGraph
from eos_ai.embedding_engine import EmbeddingEngine
```
