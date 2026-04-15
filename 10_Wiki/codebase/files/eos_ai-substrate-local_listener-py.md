---
type: codebase-file
path: eos_ai/substrate/local_listener.py
module: eos_ai.substrate.local_listener
lines: 397
size: 15578
generated: 2026-04-12
---

# eos_ai/substrate/local_listener.py

Local listener — bounded wake/activation layer for the substrate.

Purpose
-------
Today the substrate only enters open_day via cron. This module adds a small,
...

**Lines:** 397 | **Size:** 15,578 bytes

## Depends On

- [[eos_ai-substrate-nodes-py]]
- [[eos_ai-substrate-ritual_body-py]]
- [[eos_ai-substrate-ritual_runner-py]]
- [[eos_ai-substrate-rituals-py]]
- [[eos_ai-substrate-station_readiness-py]]
- [[eos_ai-substrate-storage-py]]

## Used By

- [[eos_ai-substrate-wake_producer-py]]
- [[scripts-substrate_audio_loop_smoke_test-py]]
- [[scripts-substrate_drain_station-py]]
- [[scripts-substrate_local_listener-py]]
- [[scripts-substrate_local_listener_smoke_test-py]]
- [[scripts-substrate_operator_state_smoke_test-py]]
- [[scripts-substrate_stt_producer_smoke_test-py]]
- [[scripts-substrate_voice_session_smoke_test-py]]
- [[scripts-substrate_wake_producer_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-local_listener-py-TriggerKind]] — 0 methods
- **class** [[eos_ai-substrate-local_listener-py-TriggerStatus]] — 0 methods
- **class** [[eos_ai-substrate-local_listener-py-LocalTrigger]] — 1 methods
- **class** [[eos_ai-substrate-local_listener-py-TriggerHistory]] — 6 methods
- **class** [[eos_ai-substrate-local_listener-py-LocalListener]] — 8 methods
- **fn** [[eos_ai-substrate-local_listener-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-local_listener-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-local_listener-py-_new_id]]`() → str`
- **fn** [[eos_ai-substrate-local_listener-py-get_trigger_history]]`() → TriggerHistory`
- **fn** [[eos_ai-substrate-local_listener-py-listener_report]]`(node_id, limit) → dict`

## Import Statements

```python
from __future__ import annotations
import sys
import uuid
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from threading import RLock
from typing import Optional
from eos_ai.substrate.nodes import NodeRegistry
from eos_ai.substrate.ritual_body import RitualPolicy
from eos_ai.substrate.ritual_runner import start_open_day
from eos_ai.substrate.rituals import RitualRegistry
from eos_ai.substrate.station_readiness import UNAVAILABLE
from eos_ai.substrate.station_readiness import station_readiness
from eos_ai.substrate.storage import get_storage
```
