---
type: codebase-file
path: scripts/substrate_operator_state_smoke_test.py
module: scripts.substrate_operator_state_smoke_test
lines: 243
size: 9925
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_operator_state_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Operator state engine smoke test.

Proves the bounded OperatorState layer end-to-end:

  1. Reset state: clear voice/wake/operator stores.
...

**Lines:** 243 | **Size:** 9,925 bytes

## Depends On

- [[eos_ai-substrate-local_listener-py]]
- [[eos_ai-substrate-operator_presence-py]]
- [[eos_ai-substrate-operator_state-py]]
- [[eos_ai-substrate-result_query-py]]
- [[eos_ai-substrate-ritual_body-py]]
- [[eos_ai-substrate-ritual_runner-py]]
- [[eos_ai-substrate-station_bus-py]]
- [[eos_ai-substrate-station_daemon-py]]
- [[eos_ai-substrate-voice_session-py]]
- [[eos_ai-substrate-wake_producer-py]]

## Contains

- **fn** [[scripts-substrate_operator_state_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_operator_state_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import sys
from eos_ai.substrate.local_listener import get_trigger_history
from eos_ai.substrate.operator_presence import line_for_transition
from eos_ai.substrate.operator_state import OperatorMode
from eos_ai.substrate.operator_state import get_operator_state_store
from eos_ai.substrate.operator_state import reset_operator_state_store_for_tests
from eos_ai.substrate.result_query import operator_state_snapshot
from eos_ai.substrate.ritual_body import RitualPolicy
from eos_ai.substrate.ritual_runner import finish_close_day
from eos_ai.substrate.ritual_runner import finish_open_day
from eos_ai.substrate.ritual_runner import start_close_day
from eos_ai.substrate.ritual_runner import start_open_day
from eos_ai.substrate.station_bus import get_station_bus
from eos_ai.substrate.station_daemon import StationDaemon
from eos_ai.substrate.voice_session import VoiceSessionRuntime
from eos_ai.substrate.voice_session import get_voice_session_store
from eos_ai.substrate.voice_session import reset_voice_session_store_for_tests
from eos_ai.substrate.wake_producer import get_wake_producer_history
from eos_ai.substrate.wake_producer import get_wake_producer_runtime
from eos_ai.substrate.wake_producer import reset_wake_producer_runtime_for_tests
```
