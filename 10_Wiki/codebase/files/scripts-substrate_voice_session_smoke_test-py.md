---
type: codebase-file
path: scripts/substrate_voice_session_smoke_test.py
module: scripts.substrate_voice_session_smoke_test
lines: 223
size: 9687
tags: [entry-point]
generated: 2026-04-11
---

# scripts/substrate_voice_session_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Voice session smoke test.

Proves the bounded voice-presence MVP end-to-end:
  1. A node is registered + heartbeated via StationDaemon (so SPEAK_TEXT can flow).
  2. VoiceSessionRuntime.start_session(...) opens a bounded session for ea_orchestrator.
...

**Lines:** 223 | **Size:** 9,687 bytes

## Depends On

- [[eos_ai-substrate-local_listener-py]]
- [[eos_ai-substrate-nodes-py]]
- [[eos_ai-substrate-result_query-py]]
- [[eos_ai-substrate-result_store-py]]
- [[eos_ai-substrate-station_bus-py]]
- [[eos_ai-substrate-station_daemon-py]]
- [[eos_ai-substrate-station_drainer-py]]
- [[eos_ai-substrate-voice_session-py]]

## Contains

- **fn** [[scripts-substrate_voice_session_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_voice_session_smoke_test-py-_drain]]`(node_id) → int`
- **fn** [[scripts-substrate_voice_session_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import sys
from eos_ai.substrate.local_listener import LocalListener
from eos_ai.substrate.nodes import NodeRegistry
from eos_ai.substrate.nodes import NodeStatus
from eos_ai.substrate.result_query import recent_voice_sessions
from eos_ai.substrate.result_store import get_result_store
from eos_ai.substrate.result_store import reset_result_store_for_tests
from eos_ai.substrate.station_bus import get_station_bus
from eos_ai.substrate.station_daemon import StationDaemon
from eos_ai.substrate.station_drainer import drain_results
from eos_ai.substrate.voice_session import VoiceSessionRuntime
from eos_ai.substrate.voice_session import VoiceSessionStatus
from eos_ai.substrate.voice_session import VoiceTurnSource
from eos_ai.substrate.voice_session import get_voice_session_store
from eos_ai.substrate.voice_session import reset_voice_session_store_for_tests
from eos_ai.substrate.voice_session import voice_session_report
```
