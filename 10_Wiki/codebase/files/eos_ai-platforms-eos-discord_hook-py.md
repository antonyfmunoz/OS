---
type: codebase-file
path: eos_ai/platforms/eos/discord_hook.py
module: eos_ai.platforms.eos.discord_hook
lines: 188
size: 6605
generated: 2026-05-07
---

# eos_ai/platforms/eos/discord_hook.py

Discord integration hook — thin wrapper for calling the EOS platform from Discord.

This module provides handle_eos_discord_message() which wraps:
- handle_founder_message() for intent routing
- format output for Discord delivery
...

**Lines:** 188 | **Size:** 6,605 bytes

## Depends On

- [[eos_ai-platforms-eos-ea_orchestrator-py]]
- [[eos_ai-platforms-eos-roles-py]]

## Contains

- **fn** [[eos_ai-platforms-eos-discord_hook-py-_log]]`(msg) → None`
- **fn** [[eos_ai-platforms-eos-discord_hook-py-handle_eos_discord_message]]`(text) → str`
- **fn** [[eos_ai-platforms-eos-discord_hook-py-create_ea_live_session]]`(title) → Optional[str]`
- **fn** [[eos_ai-platforms-eos-discord_hook-py-attach_founder_issue_to_live_session]]`(live_session_id, issue_text) → Optional[str]`
- **fn** [[eos_ai-platforms-eos-discord_hook-py-handle_eos_discord_live_message]]`(text) → str`
- **fn** [[eos_ai-platforms-eos-discord_hook-py-enable_discord_streaming]]`() → None`
- **fn** [[eos_ai-platforms-eos-discord_hook-py-disable_discord_streaming]]`() → None`

## Import Statements

```python
from __future__ import annotations
import sys
from typing import Optional
from eos_ai.platforms.eos.ea_orchestrator import EAResponse
from eos_ai.platforms.eos.ea_orchestrator import handle_founder_message
from eos_ai.platforms.eos.roles import EOSRole
```
