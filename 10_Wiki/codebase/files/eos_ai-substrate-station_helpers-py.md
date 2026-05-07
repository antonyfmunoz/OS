---
type: codebase-file
path: eos_ai/substrate/station_helpers.py
module: eos_ai.substrate.station_helpers
lines: 128
size: 3675
generated: 2026-05-07
---

# eos_ai/substrate/station_helpers.py

Small helpers for proposing MVP SafeActions to a named station.

Used by smoke tests, admin scripts, and scheduled rituals to drop a single
safe action on the bus without reconstructing the StationContract dance.
Everything here still routes through StationContract.propose() so the
...

**Lines:** 128 | **Size:** 3,675 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]
- [[eos_ai-substrate-station-py]]

## Used By

- [[eos_ai-substrate-ritual_body-py]]
- [[eos_ai-substrate-voice_session-py]]
- [[scripts-substrate_result_loop_smoke_test-py]]
- [[scripts-substrate_smoke_test-py]]

## Contains

- **fn** [[eos_ai-substrate-station_helpers-py-_contract_in_drive]]`(node_id) → StationContract`
- **fn** [[eos_ai-substrate-station_helpers-py-propose_speak_text]]`(node_id, text) → SafeAction`
- **fn** [[eos_ai-substrate-station_helpers-py-propose_open_url]]`(node_id, url) → SafeAction`
- **fn** [[eos_ai-substrate-station_helpers-py-propose_launch_app]]`(node_id, app_id) → SafeAction`
- **fn** [[eos_ai-substrate-station_helpers-py-propose_focus_app]]`(node_id, app_id) → SafeAction`
- **fn** [[eos_ai-substrate-station_helpers-py-propose_open_scene]]`(node_id, scene) → SafeAction`
- **fn** [[eos_ai-substrate-station_helpers-py-propose_play_sound]]`(node_id) → SafeAction`

## Import Statements

```python
from __future__ import annotations
from typing import Optional
from eos_ai.substrate.actions import ActionKind
from eos_ai.substrate.actions import SafeAction
from eos_ai.substrate.station import ControlMode
from eos_ai.substrate.station import StationContract
```
