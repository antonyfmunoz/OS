---
type: codebase-file
path: eos_ai/research_engine.py
module: eos_ai.research_engine
lines: 696
size: 29629
generated: 2026-04-12
---

# eos_ai/research_engine.py

ResearchEngine — autonomous knowledge gap detection and research layer.

The AI identifies its own knowledge gaps from interaction data and researches
them from first principles. Every solved problem becomes permanent capability
stored in the Neon skills table — injected into future relevant agent calls.
...

**Lines:** 696 | **Size:** 29,629 bytes

## Depends On

- [[eos_ai-agent_runtime-py]]
- [[eos_ai-cognitive_loop-py]]
- [[eos_ai-context-py]]
- [[eos_ai-db-py]]
- [[eos_ai-memory-py]]
- [[eos_ai-strategy_engine-py]]
- [[eos_ai-venture_knowledge-py]]

## Used By

- [[eos_ai-evolution_engine-py]]

## Contains

- **class** [[eos_ai-research_engine-py-ResearchEngine]] — 11 methods

## Import Statements

```python
import datetime
import os
import re
import sys
from pathlib import Path
from dotenv import load_dotenv
from eos_ai.context import EOSContext
from eos_ai.cognitive_loop import CognitiveLoop
from eos_ai.agent_runtime import TaskType
from eos_ai.db import get_conn
from eos_ai.memory import AgentMemory
from eos_ai.venture_knowledge import VentureKnowledgeBase
from eos_ai.strategy_engine import _parse_labeled_sections
```
