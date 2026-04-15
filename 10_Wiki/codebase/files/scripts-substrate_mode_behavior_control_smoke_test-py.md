---
type: codebase-file
path: scripts/substrate_mode_behavior_control_smoke_test.py
module: scripts.substrate_mode_behavior_control_smoke_test
lines: 338
size: 10206
generated: 2026-04-12
---

# scripts/substrate_mode_behavior_control_smoke_test.py

Smoke test — Mode Behavior + Session Control v1.

Validates:
  1. Product mode: no internal leakage
  2. Builder mode: debug/system allowed
...

**Lines:** 338 | **Size:** 10,206 bytes

## Depends On

- [[eos_ai-substrate-actions-py]]
- [[eos_ai-substrate-discord_text_transport-py]]
- [[eos_ai-substrate-mode_behavior-py]]
- [[eos_ai-substrate-session_control-py]]

## Contains

- **fn** [[scripts-substrate_mode_behavior_control_smoke_test-py-_result]]`(name, ok, detail) → None`
- **fn** [[scripts-substrate_mode_behavior_control_smoke_test-py-section]]`(title) → None`

## Import Statements

```python
import os
import sys
import importlib
import inspect
from eos_ai.substrate.mode_behavior import shape_reply
from eos_ai.substrate.mode_behavior import detect_internal_leakage
from eos_ai.substrate.session_control import clear_session
from eos_ai.substrate.session_control import reset_session
from eos_ai.substrate.session_control import get_message_count
from eos_ai.substrate.session_control import maybe_auto_clear
from eos_ai.substrate.session_control import reset_counters_for_tests
import eos_ai.substrate.mode_behavior as mb
import eos_ai.substrate.session_control as sc
from eos_ai.substrate import discord_text_transport as dtt
from eos_ai.substrate.discord_text_transport import build_tts_reply_envelope
```
