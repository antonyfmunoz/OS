---
type: codebase-file
path: eos_ai/context_compaction.py
module: eos_ai.context_compaction
lines: 224
size: 8955
generated: 2026-04-11
---

# eos_ai/context_compaction.py

ContextCompactor — seamless context window management for long conversations.

When a conversation approaches 80% of the 200k token window, this module
compresses message history into a structured brief, persists it to Neon,
and seeds the next context window. The user sees one continuous conversation;
...

**Lines:** 224 | **Size:** 8,955 bytes

## Depends On

- [[eos_ai-context-py]]
- [[eos_ai-db-py]]

## Contains

- **class** [[eos_ai-context_compaction-py-ContextCompactor]] — 7 methods
- **fn** [[eos_ai-context_compaction-py-_utcnow]]`() → str`

## Import Statements

```python
import json
import uuid
from datetime import datetime
from datetime import timezone
from eos_ai.context import EOSContext
from eos_ai.db import get_conn
```
