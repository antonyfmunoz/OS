---
type: codebase-file
path: eos_ai/substrate/station_bus.py
module: eos_ai.substrate.station_bus
lines: 188
size: 7027
generated: 2026-04-11
---

# eos_ai/substrate/station_bus.py

StationBus — MVP transport between EOS and local Station Daemons.

This is the thinnest viable transport we can ship without opening network
ports or shipping raw shell. It is explicitly a placeholder that can be
replaced with WebSocket / HTTP / Tailscale-sidecar without changing the
...

**Lines:** 188 | **Size:** 7,027 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]
- [[eos_ai-substrate-station-py]]

## Used By

- [[eos_ai-substrate-station_daemon-py]]
- [[eos_ai-substrate-station_drainer-py]]
- [[scripts-substrate_audio_loop_smoke_test-py]]
- [[scripts-substrate_discord_text_tts_smoke_test-py]]
- [[scripts-substrate_discord_voice_playback_smoke_test-py]]
- [[scripts-substrate_discord_voice_transport_smoke_test-py]]
- [[scripts-substrate_drainer_smoke_test-py]]
- [[scripts-substrate_durable_result_smoke_test-py]]
- [[scripts-substrate_google_meet_smoke_test-py]]
- [[scripts-substrate_local_listener_smoke_test-py]]
- [[scripts-substrate_meeting_attachment_smoke_test-py]]
- [[scripts-substrate_meeting_transport_smoke_test-py]]
- [[scripts-substrate_operator_state_smoke_test-py]]
- [[scripts-substrate_ptt_binding_smoke_test-py]]
- [[scripts-substrate_result_loop_smoke_test-py]]
- [[scripts-substrate_smoke_test-py]]
- [[scripts-substrate_stt_producer_smoke_test-py]]
- [[scripts-substrate_transport_report_smoke_test-py]]
- [[scripts-substrate_voice_eos_responder_smoke_test-py]]
- [[scripts-substrate_voice_session_smoke_test-py]]
- [[scripts-substrate_wake_producer_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-station_bus-py-StationBus]] — 10 methods
- **fn** [[eos_ai-substrate-station_bus-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-station_bus-py-_atomic_write_json]]`(path, data) → None`
- **fn** [[eos_ai-substrate-station_bus-py-_read_json]]`(path, default) → Any`
- **fn** [[eos_ai-substrate-station_bus-py-get_station_bus]]`() → StationBus`
- **fn** [[eos_ai-substrate-station_bus-py-reset_station_bus_for_tests]]`() → None`

## Import Statements

```python
from __future__ import annotations
import json
import os
import sys
import threading
from pathlib import Path
from typing import Any
from typing import Optional
from eos_ai.substrate.actions import SafeAction
from eos_ai.substrate.actions import ActionResult
from eos_ai.substrate.actions import ActionStatus
from eos_ai.substrate.station import StationEvent
```
