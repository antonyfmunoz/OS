---
type: codebase-file
path: eos_ai/strategy_engine.py
module: eos_ai.strategy_engine
lines: 526
size: 22264
generated: 2026-04-12
---

# eos_ai/strategy_engine.py

StrategyEngine — first-principles strategic reasoning layer.
DecisionEngine  — structured 6-step decision evaluation.

These are the intelligence layers that elevate the AI from
operational to genuinely strategic. They reason about market
...

**Lines:** 526 | **Size:** 22,264 bytes

## Depends On

- [[eos_ai-agent_runtime-py]]
- [[eos_ai-cognitive_loop-py]]
- [[eos_ai-context-py]]
- [[eos_ai-db-py]]
- [[eos_ai-memory-py]]
- [[eos_ai-venture_knowledge-py]]

## Used By

- [[eos_ai-reality_engine-py]]
- [[eos_ai-research_engine-py]]

## Contains

- **class** [[eos_ai-strategy_engine-py-StrategyEngine]] — 5 methods
- **class** [[eos_ai-strategy_engine-py-DecisionEngine]] — 2 methods
- **fn** [[eos_ai-strategy_engine-py-_query_30d_stats]]`(org_id, venture_id) → dict`
- **fn** [[eos_ai-strategy_engine-py-_parse_labeled_sections]]`(text, keys) → dict`

## Import Statements

```python
import datetime
import json
import os
import sys
from pathlib import Path
from eos_ai.context import EOSContext
from eos_ai.context import load_context_from_env
from eos_ai.cognitive_loop import CognitiveLoop
from eos_ai.agent_runtime import TaskType
from eos_ai.db import get_conn
from eos_ai.db import resolve_venture
from eos_ai.memory import AgentMemory
from eos_ai.venture_knowledge import VentureKnowledgeBase
```
