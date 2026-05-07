---
type: codebase-file
path: eos_ai/substrate/station_triggers.py
module: eos_ai.substrate.station_triggers
lines: 382
size: 14259
generated: 2026-05-07
---

# eos_ai/substrate/station_triggers.py

Station triggers — event history and control-plane dispatch for
wake word, clap, manual, and Discord triggers.

Builds on top of voice_wake.py (which stores *current state*) by adding:
  1. A bounded event store for trigger history.
...

**Lines:** 382 | **Size:** 14,259 bytes

## Contains

- **class** [[eos_ai-substrate-station_triggers-py-StationTriggerType]] — 0 methods
- **class** [[eos_ai-substrate-station_triggers-py-StationTriggerEvent]] — 3 methods
- **class** [[eos_ai-substrate-station_triggers-py-StationTriggerStore]] — 9 methods
- **fn** [[eos_ai-substrate-station_triggers-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-station_triggers-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-station_triggers-py-_new_id]]`() → str`
- **fn** [[eos_ai-substrate-station_triggers-py-register_station_trigger]]`(trigger_type, phrase) → StationTriggerEvent`
- **fn** [[eos_ai-substrate-station_triggers-py-handle_station_trigger]]`(trigger_type, phrase) → dict[str, Any]`

## Import Statements

```python
from __future__ import annotations
import sys
import threading
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Optional
```
