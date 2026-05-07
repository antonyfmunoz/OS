---
type: codebase-file
path: eos_ai/substrate/station_presence.py
module: eos_ai.substrate.station_presence
lines: 335
size: 12259
generated: 2026-05-07
---

# eos_ai/substrate/station_presence.py

Station presence — unified station posture and availability state.

Combines node availability, wake/clap/tts flags, control mode, and
operator presence mode into a single queryable singleton.  This is the
"where is the operator and what's available" question answered in one
...

**Lines:** 335 | **Size:** 12,259 bytes

## Contains

- **class** [[eos_ai-substrate-station_presence-py-StationPresenceMode]] — 0 methods
- **class** [[eos_ai-substrate-station_presence-py-StationPresence]] — 3 methods
- **class** [[eos_ai-substrate-station_presence-py-StationPresenceStore]] — 7 methods
- **fn** [[eos_ai-substrate-station_presence-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-station_presence-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-station_presence-py-_new_id]]`() → str`
- **fn** [[eos_ai-substrate-station_presence-py-get_station_presence]]`() → StationPresence`
- **fn** [[eos_ai-substrate-station_presence-py-update_station_presence]]`() → StationPresence`
- **fn** [[eos_ai-substrate-station_presence-py-set_presence_mode]]`(mode) → StationPresence`
- **fn** [[eos_ai-substrate-station_presence-py-mark_local_available]]`() → StationPresence`
- **fn** [[eos_ai-substrate-station_presence-py-mark_local_unavailable]]`() → StationPresence`
- **fn** [[eos_ai-substrate-station_presence-py-get_station_summary]]`() → dict`

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
from typing import Optional
```
