---
type: codebase-file
path: eos_ai/substrate/playback_status.py
module: eos_ai.substrate.playback_status
lines: 93
size: 2515
generated: 2026-04-12
---

# eos_ai/substrate/playback_status.py

Shared playback status snapshot shape for voice transports.

This module defines a single JSON-friendly shape that both the Discord
voice transport and the meeting voice transport emit via their
``status_report()`` methods. Operators get one contract per transport
...

**Lines:** 93 | **Size:** 2,515 bytes

## Contains

- **class** [[eos_ai-substrate-playback_status-py-PlaybackStatusSnapshot]] — 1 methods
- **fn** [[eos_ai-substrate-playback_status-py-make_playback_status_snapshot]]`() → PlaybackStatusSnapshot`
- **fn** [[eos_ai-substrate-playback_status-py-aggregate_by_status]]`(history_rows) → dict[str, int]`

## Import Statements

```python
from __future__ import annotations
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Optional
```
