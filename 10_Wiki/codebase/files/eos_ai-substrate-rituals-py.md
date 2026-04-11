---
type: codebase-file
path: eos_ai/substrate/rituals.py
module: eos_ai.substrate.rituals
lines: 214
size: 8302
generated: 2026-04-11
---

# eos_ai/substrate/rituals.py

Ritual workflow scaffold — open_day / close_day.

Rituals are named, stateful workflows that run at specific points in the
founder's day. They coordinate multiple agents/components (briefings, handoffs,
summaries) without each cron script reinventing structure.
...

**Lines:** 214 | **Size:** 8,302 bytes

## Used By

- [[eos_ai-substrate-local_listener-py]]
- [[eos_ai-substrate-ritual_body-py]]
- [[eos_ai-substrate-ritual_reconciler-py]]
- [[eos_ai-substrate-ritual_runner-py]]
- [[scripts-substrate_durable_result_smoke_test-py]]
- [[scripts-substrate_local_listener_smoke_test-py]]
- [[scripts-substrate_result_loop_smoke_test-py]]
- [[scripts-substrate_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-rituals-py-RitualKind]] — 0 methods
- **class** [[eos_ai-substrate-rituals-py-RitualState]] — 0 methods
- **class** [[eos_ai-substrate-rituals-py-Ritual]] — 1 methods
- **class** [[eos_ai-substrate-rituals-py-RitualRegistry]] — 13 methods
- **fn** [[eos_ai-substrate-rituals-py-_new_id]]`() → str`
- **fn** [[eos_ai-substrate-rituals-py-_utcnow]]`() → str`

## Import Statements

```python
from __future__ import annotations
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Optional
```
