---
type: codebase-file
path: eos_ai/skill_improvement.py
module: eos_ai.skill_improvement
lines: 449
size: 19175
generated: 2026-05-07
---

# eos_ai/skill_improvement.py

SkillImprovementEngine — RLHF-driven skill rewriting + self-organization.

Monitors outcome data in memory.db and automatically rewrites underperforming
skill files using examples of what worked vs what didn't.

...

**Lines:** 449 | **Size:** 19,175 bytes

## Depends On

- [[eos_ai-agent_runtime-py]]
- [[eos_ai-skill_registry-py]]

## Used By

- [[eos_ai-evolution_engine-py]]

## Contains

- **class** [[eos_ai-skill_improvement-py-SkillImprovementEngine]] — 9 methods

## Import Statements

```python
import json
import os
import shutil
import sys
from datetime import datetime
from datetime import timezone
from datetime import timedelta
from pathlib import Path
from eos_ai.agent_runtime import AgentRuntime
from eos_ai.agent_runtime import TaskType
from eos_ai.skill_registry import SkillRegistry
from eos_ai.skill_registry import get_skill_registry
from eos_ai.skill_registry import reset_skill_registry
```
