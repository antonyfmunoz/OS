---
type: codebase-file
path: eos_ai/business_instance.py
module: eos_ai.business_instance
lines: 490
size: 19263
generated: 2026-04-12
---

# eos_ai/business_instance.py

BusinessInstance — venture-stage context layer.

Tracks where a venture is in its growth journey (Stage 1–6),
the offer, ICP, and channels. Injected into agent prompts
to give context-aware guidance at every stage.
...

**Lines:** 490 | **Size:** 19,263 bytes

## Used By

- [[services-discord_bot-py]]

## Contains

- **class** [[eos_ai-business_instance-py-BusinessInstance]] — 0 methods
- **class** [[eos_ai-business_instance-py-BusinessInstanceManager]] — 9 methods
- **fn** [[eos_ai-business_instance-py-get_ai_name]]`(ctx, venture_id) → str`

## Import Statements

```python
from dataclasses import dataclass
from dataclasses import field
from dataclasses import asdict
from typing import Optional
import json
from datetime import datetime
from datetime import timezone
```
