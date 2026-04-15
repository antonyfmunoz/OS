---
type: codebase-file
path: scripts/substrate_wake_producer_smoke_test.py
module: scripts.substrate_wake_producer_smoke_test
lines: 222
size: 8994
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_wake_producer_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Wake producer smoke test.

Proves the bounded wake producer layer end-to-end:

  1. Reset state: clear voice session store, wake producer history, trigger history.
...

**Lines:** 222 | **Size:** 8,994 bytes

## Depends On

- [[eos_ai-substrate-local_listener-py]]
- [[eos_ai-substrate-result_query-py]]
- [[eos_ai-substrate-station_bus-py]]
- [[eos_ai-substrate-station_daemon-py]]
- [[eos_ai-substrate-voice_session-py]]
- [[eos_ai-substrate-wake_producer-py]]

## Contains

- **fn** [[scripts-substrate_wake_producer_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_wake_producer_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import sys
from eos_ai.substrate.local_listener import get_trigger_history
from eos_ai.substrate.result_query import recent_wake_producer_events
from eos_ai.substrate.station_bus import get_station_bus
from eos_ai.substrate.station_daemon import StationDaemon
from eos_ai.substrate.voice_session import VoiceSessionStatus
from eos_ai.substrate.voice_session import VoiceTurnSource
from eos_ai.substrate.voice_session import get_voice_session_store
from eos_ai.substrate.voice_session import reset_voice_session_store_for_tests
from eos_ai.substrate.wake_producer import WakeProducerKind
from eos_ai.substrate.wake_producer import get_wake_producer_history
from eos_ai.substrate.wake_producer import get_wake_producer_runtime
from eos_ai.substrate.wake_producer import reset_wake_producer_runtime_for_tests
from eos_ai.substrate.wake_producer import resolve_role_hint
```
