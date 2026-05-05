---
type: codebase-file
path: eos_ai/user_model.py
module: eos_ai.user_model
lines: 460
size: 19062
generated: 2026-04-12
---

# eos_ai/user_model.py

UserModel — learns how the founder thinks, communicates, and makes decisions.

Closes the intent-expression gap: the difference between what he says and
what he means. Profiles built from 30-day interaction history in Neon.
Trust level grows with interaction volume — higher trust unlocks aggressive
...

**Lines:** 460 | **Size:** 19,062 bytes

## Depends On

- [[eos_ai-agent_runtime-py]]
- [[eos_ai-cognitive_loop-py]]
- [[eos_ai-context-py]]
- [[eos_ai-db-py]]

## Contains

- **class** [[eos_ai-user_model-py-UserModel]] — 8 methods

## Import Statements

```python
import json
import os
import sys
import datetime
from pathlib import Path
from dotenv import load_dotenv
from eos_ai.context import EOSContext
from eos_ai.cognitive_loop import CognitiveLoop
from eos_ai.agent_runtime import AgentRuntime
from eos_ai.agent_runtime import TaskType
from eos_ai.db import get_conn
```
