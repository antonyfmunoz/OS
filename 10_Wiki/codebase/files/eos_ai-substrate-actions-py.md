---
type: codebase-file
path: eos_ai/substrate/actions.py
module: eos_ai.substrate.actions
lines: 119
size: 4241
generated: 2026-04-12
---

# eos_ai/substrate/actions.py

SafeAction schema — structured intents for future local execution.

The substrate must NEVER ship raw shell commands to a local node. Instead the
VPS emits typed *intents* and the Station Daemon interprets them. This keeps
the trust boundary clean: the local node is the only thing that can touch the
...

**Lines:** 119 | **Size:** 4,241 bytes

## Used By

- [[eos_ai-substrate-claude_responder-py]]
- [[eos_ai-substrate-control_bridge-py]]
- [[eos_ai-substrate-local_executor-py]]
- [[eos_ai-substrate-operator_interface-py]]
- [[eos_ai-substrate-remote_executor-py]]
- [[eos_ai-substrate-remote_identity-py]]
- [[eos_ai-substrate-ritual_body-py]]
- [[eos_ai-substrate-scene_capabilities-py]]
- [[eos_ai-substrate-scenes-py]]
- [[eos_ai-substrate-station-py]]
- [[eos_ai-substrate-station_bus-py]]
- [[eos_ai-substrate-station_daemon-py]]
- [[eos_ai-substrate-station_helpers-py]]
- [[scripts-substrate_claude_responder_smoke_test-py]]
- [[scripts-substrate_claude_session_bridge_smoke_test-py]]
- [[scripts-substrate_claude_session_cli-py]]
- [[scripts-substrate_control_layer_smoke_test-py]]
- [[scripts-substrate_coordination_intelligence_smoke_test-py]]
- [[scripts-substrate_discord_claude_hardswitch_smoke_test-py]]
- [[scripts-substrate_discord_tts_body_only_smoke_test-py]]
- [[scripts-substrate_drainer_smoke_test-py]]
- [[scripts-substrate_durable_result_smoke_test-py]]
- [[scripts-substrate_execution_intelligence_smoke_test-py]]
- [[scripts-substrate_execution_linkage_smoke_test-py]]
- [[scripts-substrate_meeting_intelligence_smoke_test-py]]
- [[scripts-substrate_meeting_intelligence_upgrade_smoke_test-py]]
- [[scripts-substrate_mode_behavior_control_smoke_test-py]]
- [[scripts-substrate_operator_cli-py]]
- [[scripts-substrate_operator_interface_smoke_test-py]]
- [[scripts-substrate_product_linkage_smoke_test-py]]
- [[scripts-substrate_remote_execution_smoke_test-py]]
- [[scripts-substrate_remote_executor_daemon-py]]
- [[scripts-substrate_resolution_intelligence_smoke_test-py]]
- [[scripts-substrate_session_soul_doc_smoke_test-py]]
- [[scripts-substrate_temporal_intelligence_smoke_test-py]]

## Contains

- **class** [[eos_ai-substrate-actions-py-ActionKind]] — 0 methods
- **class** [[eos_ai-substrate-actions-py-ActionStatus]] — 0 methods
- **class** [[eos_ai-substrate-actions-py-SafeAction]] — 1 methods
- **class** [[eos_ai-substrate-actions-py-ActionResult]] — 0 methods
- **fn** [[eos_ai-substrate-actions-py-_new_id]]`() → str`
- **fn** [[eos_ai-substrate-actions-py-_utcnow]]`() → str`

## Import Statements

```python
from __future__ import annotations
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from enum import Enum
from typing import Any
from typing import Optional
```
