---
type: codebase-file
path: eos_ai/substrate/discord_mode_routing.py
module: eos_ai.substrate.discord_mode_routing
lines: 336
size: 11531
generated: 2026-05-07
---

# eos_ai/substrate/discord_mode_routing.py

Discord Channel Mode Routing v1 — bounded channel→mode classification.

Purpose
-------
EOS exposes two operating modes on Discord, selected by which channel a
...

**Lines:** 336 | **Size:** 11,531 bytes

## Used By

- [[scripts-direct_watcher_path_smoke_test-py]]

## Contains

- **fn** [[eos_ai-substrate-discord_mode_routing-py-_parse_id_set]]`(env_name) → set[str]`
- **fn** [[eos_ai-substrate-discord_mode_routing-py-_flag_truthy]]`(env_name) → bool`
- **fn** [[eos_ai-substrate-discord_mode_routing-py-_norm_target]]`(raw) → str`
- **fn** [[eos_ai-substrate-discord_mode_routing-py-resolve_discord_mode]]`(guild_id, channel_id) → str`
- **fn** [[eos_ai-substrate-discord_mode_routing-py-resolve_mode_session]]`(mode, guild_id, channel_id, metadata) → dict[str, Any]`
- **fn** [[eos_ai-substrate-discord_mode_routing-py-current_mode_context]]`() → Optional[dict[str, Any]]`
- **fn** [[eos_ai-substrate-discord_mode_routing-py-mode_context]]`(mode)`
- **fn** [[eos_ai-substrate-discord_mode_routing-py-clear_mode_context_for_tests]]`() → None`

## Import Statements

```python
from __future__ import annotations
import os
import threading
from contextlib import contextmanager
from typing import Any
from typing import Optional
```
