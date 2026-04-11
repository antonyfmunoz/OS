---
type: codebase-file
path: eos_ai/stage_manager.py
module: eos_ai.stage_manager
lines: 297
size: 10719
generated: 2026-04-11
---

# eos_ai/stage_manager.py

StageManager — auto-updates Notion, Discord, and primitives when stage advances.

When the founder says "I closed my first client" or "advance to stage 2",
gateway.py detects it and calls StageManager.advance_stage().

...

**Lines:** 297 | **Size:** 10,719 bytes

## Depends On

- [[eos_ai-context-py]]

## Contains

- **class** [[eos_ai-stage_manager-py-StageTransitionResult]] — 0 methods
- **class** [[eos_ai-stage_manager-py-StageManager]] — 4 methods
- **fn** [[eos_ai-stage_manager-py-detect_stage_transition]]`(text) → dict`

## Import Statements

```python
import os
import sys
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from eos_ai.context import EOSContext
```
