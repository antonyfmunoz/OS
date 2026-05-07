---
type: codebase-file
path: scripts/session_discord_control_smoke_test.py
module: scripts.session_discord_control_smoke_test
lines: 279
size: 10558
generated: 2026-05-07
---

# scripts/session_discord_control_smoke_test.py

Smoke tests for the interactive Discord control layer.

Tests: state detection patterns, event formatting, button views,
channel routing, option extraction, timeout config, and watcher
activity tracking.
...

**Lines:** 279 | **Size:** 10,558 bytes

## Depends On

- [[eos_ai-substrate-session_discord_bridge-py]]
- [[eos_ai-substrate-session_watcher-py]]

## Contains

- **fn** [[scripts-session_discord_control_smoke_test-py-check]]`(name, condition) → None`

## Import Statements

```python
import os
import sys
import time
from dotenv import load_dotenv
from eos_ai.substrate.session_watcher import SessionState
from eos_ai.substrate.session_watcher import SessionWatcher
from eos_ai.substrate.session_watcher import WatcherEvent
from eos_ai.substrate.session_watcher import _PLAN_PATTERNS
from eos_ai.substrate.session_watcher import _PERMISSION_PATTERNS
from eos_ai.substrate.session_watcher import _QUESTION_PATTERNS
from eos_ai.substrate.session_discord_bridge import LAYER_VERSION
from eos_ai.substrate.session_discord_bridge import PlanApprovalView
from eos_ai.substrate.session_discord_bridge import PermissionView
from eos_ai.substrate.session_discord_bridge import QuestionOptionView
from eos_ai.substrate.session_discord_bridge import format_event
from eos_ai.substrate.session_discord_bridge import _extract_options
from eos_ai.substrate.session_discord_bridge import _resolve_channel_id
from eos_ai.substrate.session_discord_bridge import _BUTTON_TIMEOUT
from eos_ai.substrate.session_discord_bridge import _BUILDER_SESSION
from eos_ai.substrate.session_discord_bridge import _PRODUCT_SESSION
```
