---
type: codebase-file
path: eos_ai/accountability.py
module: eos_ai.accountability
lines: 189
size: 6630
generated: 2026-05-07
---

# eos_ai/accountability.py

AccountabilityEngine — holds the founder to their word.

When a founder commits to something ("I'll send 20 DMs today"),
this engine logs it and schedules a follow-up. The proactive engine
fires that follow-up at the right time through Telegram or Discord.
...

**Lines:** 189 | **Size:** 6,630 bytes

## Used By

- [[core-action_system-control_plane-py]]
- [[scripts-substrate_router_claude_primary_smoke_test-py]]

## Contains

- **class** [[eos_ai-accountability-py-Commitment]] — 0 methods
- **class** [[eos_ai-accountability-py-AccountabilityEngine]] — 6 methods

## Import Statements

```python
import json
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timedelta
```
