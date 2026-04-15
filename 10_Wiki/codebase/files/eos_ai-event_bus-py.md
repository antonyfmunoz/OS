---
type: codebase-file
path: eos_ai/event_bus.py
module: eos_ai.event_bus
lines: 510
size: 19074
tags: [entry-point]
generated: 2026-04-12
---

# eos_ai/event_bus.py

> **ENTRY POINT** — Contains `if __name__` or server start.

EventBus — reactive coordination layer for EOS agents.

Decouples event producers (icp_scorer, dm_monitor, calendly_webhook) from
consumers (agents, orchestrator, memory). Any component can publish a business
event; registered handlers fire synchronously or in a background thread.
...

**Lines:** 510 | **Size:** 19,074 bytes

## Depends On

- [[eos_ai-db-py]]

## Used By

- [[eos_ai-coordination_engine-py]]
- [[eos_ai-reality_engine-py]]
- [[scripts-substrate_drainer_smoke_test-py]]

## Contains

- **class** [[eos_ai-event_bus-py-EventBus]] — 5 methods
- **class** [[eos_ai-event_bus-py-EventRegistry]] — 2 methods
- **fn** [[eos_ai-event_bus-py-_utcnow]]`() → str`
- **fn** [[eos_ai-event_bus-py-_handle_new_lead]]`(payload) → dict`
- **fn** [[eos_ai-event_bus-py-_handle_lead_replied]]`(payload) → dict`
- **fn** [[eos_ai-event_bus-py-_handle_lead_booked]]`(payload) → dict`
- **fn** [[eos_ai-event_bus-py-_handle_lead_closed]]`(payload) → dict`
- **fn** [[eos_ai-event_bus-py-_handle_lead_lost]]`(payload) → dict`
- **fn** [[eos_ai-event_bus-py-_handle_signal_captured]]`(payload) → dict`
- **fn** [[eos_ai-event_bus-py-_handle_content_needed]]`(payload) → dict`
- **fn** [[eos_ai-event_bus-py-_handle_morning_cycle]]`(payload) → dict`
- **fn** [[eos_ai-event_bus-py-_handle_skill_threshold]]`(payload) → dict`
- **fn** [[eos_ai-event_bus-py-get_bus]]`() → EventBus`

## Import Statements

```python
import json
import threading
from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Callable
import sys
import os
from eos_ai.db import get_conn
from eos_ai.db import ORG_ID
```
