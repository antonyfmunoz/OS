---
type: codebase-file
path: eos_ai/evolution_engine.py
module: eos_ai.evolution_engine
lines: 869
size: 35284
generated: 2026-04-11
---

# eos_ai/evolution_engine.py

EvolutionEngine — continuous self-improvement beyond skill rewrites.

Combines two concerns:
  1. Stage-primitive lifecycle — tracks which KnowledgePrimitives are
     active at the venture's current stage, what unlocks next, and
...

**Lines:** 869 | **Size:** 35,284 bytes

## Depends On

- [[eos_ai-agent_runtime-py]]
- [[eos_ai-cognitive_loop-py]]
- [[eos_ai-context-py]]
- [[eos_ai-db-py]]
- [[eos_ai-research_engine-py]]
- [[eos_ai-skill_improvement-py]]

## Contains

- **class** [[eos_ai-evolution_engine-py-EvolutionEngine]] — 13 methods

## Import Statements

```python
import json
import os
import sys
import uuid
import datetime
from pathlib import Path
from dotenv import load_dotenv
from eos_ai.context import EOSContext
from eos_ai.cognitive_loop import CognitiveLoop
from eos_ai.agent_runtime import AgentRuntime
from eos_ai.agent_runtime import TaskType
from eos_ai.skill_improvement import SkillImprovementEngine
from eos_ai.research_engine import ResearchEngine
from eos_ai.db import get_conn
```
