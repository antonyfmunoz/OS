---
type: codebase-file
path: eos_ai/human_intelligence.py
module: eos_ai.human_intelligence
lines: 714
size: 32473
generated: 2026-04-11
---

# eos_ai/human_intelligence.py

HumanIntelligenceEngine — behavioral profiling for every person the system
interacts with.

Reads lead files from 03_CRM/Leads/, synthesizes communication style,
dominant pain, objection risk, and next best action into a stored profile.
...

**Lines:** 714 | **Size:** 32,473 bytes

## Depends On

- [[eos_ai-agent_runtime-py]]
- [[eos_ai-context-py]]
- [[eos_ai-db-py]]

## Used By

- [[eos_ai-onboarding_backfill-py]]

## Contains

- **class** [[eos_ai-human_intelligence-py-HumanIntelligenceEngine]] — 16 methods
- **fn** [[eos_ai-human_intelligence-py-_utcnow]]`() → str`
- **fn** [[eos_ai-human_intelligence-py-format_profile]]`(profile) → str`

## Import Statements

```python
import glob
import json
import os
import re
import sys
import datetime
from pathlib import Path
from typing import Literal
from eos_ai.agent_runtime import AgentRuntime
from eos_ai.agent_runtime import TaskType
from eos_ai.context import EOSContext
from eos_ai.context import load_context_from_env
from eos_ai.db import get_conn
from eos_ai.db import resolve_venture
from eos_ai.db import ORG_ID
from eos_ai.db import USER_ID
```
