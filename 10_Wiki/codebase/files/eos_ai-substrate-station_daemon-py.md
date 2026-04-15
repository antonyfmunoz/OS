---
type: codebase-file
path: eos_ai/substrate/station_daemon.py
module: eos_ai.substrate.station_daemon
lines: 749
size: 28982
tags: [entry-point]
generated: 2026-04-12
---

# eos_ai/substrate/station_daemon.py

> **ENTRY POINT** — Contains `if __name__` or server start.

StationDaemon — minimal local node execution loop.

This is the smallest viable real implementation of a local Station Daemon.
It runs on a workstation (or on the VPS for development), polls the
StationBus outbox for SafeActions addressed to its node_id, executes the
...

**Lines:** 749 | **Size:** 28,982 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]
- [[eos_ai-substrate-app_allowlist-py]]
- [[eos_ai-substrate-nodes-py]]
- [[eos_ai-substrate-scenes-py]]
- [[eos_ai-substrate-station-py]]
- [[eos_ai-substrate-station_bus-py]]

## Used By

- [[scripts-substrate_audio_loop_smoke_test-py]]
- [[scripts-substrate_discord_text_tts_smoke_test-py]]
- [[scripts-substrate_discord_voice_playback_smoke_test-py]]
- [[scripts-substrate_discord_voice_transport_smoke_test-py]]
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

- **class** [[eos_ai-substrate-station_daemon-py-_HandlerOutcome]] — 0 methods
- **class** [[eos_ai-substrate-station_daemon-py-StationDaemon]] — 17 methods
- **fn** [[eos_ai-substrate-station_daemon-py-_log]]`(msg) → None`
- **fn** [[eos_ai-substrate-station_daemon-py-_utcnow]]`() → str`
- **fn** [[eos_ai-substrate-station_daemon-py-_build_arg_parser]]`() → argparse.ArgumentParser`
- **fn** [[eos_ai-substrate-station_daemon-py-main]]`(argv) → int`

## Import Statements

```python
from __future__ import annotations
import argparse
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Callable
from typing import Optional
from urllib.parse import urlparse
from eos_ai.substrate.actions import ActionKind
from eos_ai.substrate.actions import ActionResult
from eos_ai.substrate.actions import ActionStatus
from eos_ai.substrate.actions import SafeAction
from eos_ai.substrate.app_allowlist import resolve_app
from eos_ai.substrate.nodes import Node
from eos_ai.substrate.nodes import NodeRegistry
from eos_ai.substrate.nodes import NodeStatus
from eos_ai.substrate.nodes import NodeType
from eos_ai.substrate.scenes import Scene
from eos_ai.substrate.scenes import SceneStep
from eos_ai.substrate.scenes import get_scene
from eos_ai.substrate.station import StationEvent
from eos_ai.substrate.station_bus import StationBus
from eos_ai.substrate.station_bus import get_station_bus
```
