---
type: codebase-file
path: eos_ai/self_awareness.py
module: eos_ai.self_awareness
lines: 699
size: 27322
generated: 2026-04-12
---

# eos_ai/self_awareness.py

SelfAwarenessEngine — EOS auto-reorganizes itself when anything changes.

Every state change has consequences across Discord, Notion, agents, and config.
This engine handles all of them automatically without being told.

...

**Lines:** 699 | **Size:** 27,322 bytes

## Contains

- **class** [[eos_ai-self_awareness-py-ChangeType]] — 0 methods
- **class** [[eos_ai-self_awareness-py-SystemChange]] — 0 methods
- **class** [[eos_ai-self_awareness-py-SelfAwarenessEngine]] — 5 methods

## Import Statements

```python
import os
import sys
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from enum import Enum
from typing import Any
from typing import Optional
from dotenv import load_dotenv
```
