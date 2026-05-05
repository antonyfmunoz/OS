---
type: codebase-file
path: scripts/substrate_transport_report_smoke_test.py
module: scripts.substrate_transport_report_smoke_test
lines: 195
size: 7138
tags: [entry-point]
generated: 2026-04-12
---

# scripts/substrate_transport_report_smoke_test.py

> **ENTRY POINT** — Contains `if __name__` or server start.

Unified transport report smoke test.

Proves that the unified report joins both transport fronts cleanly:
  1. A local PTT validation runs against a workstation node and lands
     in the audio_loop ring buffer.
...

**Lines:** 195 | **Size:** 7,138 bytes

## Depends On

- [[eos_ai-substrate-audio_loop-py]]
- [[eos_ai-substrate-discord_voice_transport-py]]
- [[eos_ai-substrate-nodes-py]]
- [[eos_ai-substrate-ptt_binding-py]]
- [[eos_ai-substrate-station_bus-py]]
- [[eos_ai-substrate-station_daemon-py]]
- [[eos_ai-substrate-stt_producer-py]]
- [[eos_ai-substrate-transport_report-py]]
- [[eos_ai-substrate-voice_session-py]]

## Contains

- **fn** [[scripts-substrate_transport_report_smoke_test-py-_header]]`(msg) → None`
- **fn** [[scripts-substrate_transport_report_smoke_test-py-_register_node]]`(node_id) → None`
- **fn** [[scripts-substrate_transport_report_smoke_test-py-main]]`() → int`

## Import Statements

```python
from __future__ import annotations
import sys
from eos_ai.substrate.audio_loop import reset_audio_loop_store_for_tests
from eos_ai.substrate.discord_voice_transport import DiscordVoiceTransport
from eos_ai.substrate.discord_voice_transport import reset_default_discord_voice_transports_for_tests
from eos_ai.substrate.discord_voice_transport import reset_transport_history_for_tests
from eos_ai.substrate.nodes import NodeRegistry
from eos_ai.substrate.nodes import NodeStatus
from eos_ai.substrate.ptt_binding import reset_validation_history_for_tests
from eos_ai.substrate.ptt_binding import validate_real_capture
from eos_ai.substrate.station_bus import get_station_bus
from eos_ai.substrate.station_daemon import StationDaemon
from eos_ai.substrate.stt_producer import reset_local_stt_runtime_for_tests
from eos_ai.substrate.stt_producer import reset_stt_capture_history_for_tests
from eos_ai.substrate.transport_report import unified_transport_report
from eos_ai.substrate.voice_session import get_voice_session_store
from eos_ai.substrate.voice_session import reset_voice_session_store_for_tests
```
