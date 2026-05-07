---
type: codebase-file
path: scripts/substrate_ptt_binding_smoke_test.py
module: scripts.substrate_ptt_binding_smoke_test
lines: 178
size: 6758
tags: [entry-point]
generated: 2026-05-07
---

# scripts/substrate_ptt_binding_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

PTT binding smoke test.

Proves the bounded REAL_READY proof path end-to-end:
  1. stt_workstation_readiness() returns a known classification.
  2. validate_real_capture(...) on a degraded environment with a
...

**Lines:** 178 | **Size:** 6,758 bytes

## Depends On

- [[eos_ai-substrate-audio_loop-py]]
- [[eos_ai-substrate-nodes-py]]
- [[eos_ai-substrate-ptt_binding-py]]
- [[eos_ai-substrate-station_bus-py]]
- [[eos_ai-substrate-station_daemon-py]]
- [[eos_ai-substrate-stt_producer-py]]
- [[eos_ai-substrate-voice_session-py]]

## Contains

- **fn** [[scripts-substrate_ptt_binding_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_ptt_binding_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import sys
from eos_ai.substrate.audio_loop import get_audio_loop_store
from eos_ai.substrate.audio_loop import reset_audio_loop_store_for_tests
from eos_ai.substrate.nodes import NodeRegistry
from eos_ai.substrate.nodes import NodeStatus
from eos_ai.substrate.ptt_binding import real_capture_report
from eos_ai.substrate.ptt_binding import reset_validation_history_for_tests
from eos_ai.substrate.ptt_binding import validate_real_capture
from eos_ai.substrate.station_bus import get_station_bus
from eos_ai.substrate.station_daemon import StationDaemon
from eos_ai.substrate.stt_producer import reset_local_stt_runtime_for_tests
from eos_ai.substrate.stt_producer import reset_stt_capture_history_for_tests
from eos_ai.substrate.stt_producer import stt_workstation_readiness
from eos_ai.substrate.voice_session import get_voice_session_store
from eos_ai.substrate.voice_session import reset_voice_session_store_for_tests
```
