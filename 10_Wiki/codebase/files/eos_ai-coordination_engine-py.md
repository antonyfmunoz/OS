---
type: codebase-file
path: eos_ai/coordination_engine.py
module: eos_ai.coordination_engine
lines: 400
size: 14953
generated: 2026-04-11
---

# eos_ai/coordination_engine.py

CoordinationEngine — event-driven task coordination for AI agents and humans.

Manages task assignment, tracking, and CEO-level delegation across the EOS
system. Agents and human team members share the same task queue.

...

**Lines:** 400 | **Size:** 14,953 bytes

## Depends On

- [[eos_ai-authority_engine-py]]
- [[eos_ai-context-py]]
- [[eos_ai-db-py]]
- [[eos_ai-event_bus-py]]

## Contains

- **class** [[eos_ai-coordination_engine-py-CoordinationEngine]] — 6 methods
- **fn** [[eos_ai-coordination_engine-py-_utcnow]]`() → str`
- **fn** [[eos_ai-coordination_engine-py-_notify]]`(text) → None`

## Import Statements

```python
import json
from datetime import datetime
from datetime import timezone
from pathlib import Path
from dotenv import load_dotenv
from eos_ai.context import EOSContext
from eos_ai.db import get_conn
from eos_ai.db import resolve_venture
from eos_ai.event_bus import EventBus
from eos_ai.authority_engine import AuthorityEngine
```
