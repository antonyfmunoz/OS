---
type: codebase-file
path: eos_ai/substrate/station.py
module: eos_ai.substrate.station
lines: 228
size: 9539
generated: 2026-05-07
---

# eos_ai/substrate/station.py

Station Daemon contract.

Defines the substrate-side interface between EOS (running on the VPS) and a
future local Station Daemon running on the founder's workstation. This module
contains NO daemon implementation — only the protocol/schema both sides will
...

**Lines:** 228 | **Size:** 9,539 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]

## Used By

- [[eos_ai-substrate-station_bus-py]]
- [[eos_ai-substrate-station_daemon-py]]
- [[eos_ai-substrate-station_drainer-py]]
- [[eos_ai-substrate-station_helpers-py]]
- [[scripts-substrate_drainer_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-station-py-ControlMode]] — 0 methods
- **class** [[eos_ai-substrate-station-py-StationHeartbeat]] — 0 methods
- **class** [[eos_ai-substrate-station-py-StationEvent]] — 0 methods
- **class** [[eos_ai-substrate-station-py-StationContract]] — 8 methods
- **fn** [[eos_ai-substrate-station-py-_utcnow]]`() → str`

## Import Statements

```python
from __future__ import annotations
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Optional
from eos_ai.substrate.actions import SafeAction
from eos_ai.substrate.actions import ActionResult
from eos_ai.substrate.actions import ActionKind
from eos_ai.substrate.actions import ActionStatus
```
