---
type: codebase-function
file: eos_ai/substrate/session_discord_bridge.py
line: 268
generated: 2026-05-07
---

# format_event

**File:** [[eos_ai-substrate-session_discord_bridge-py]] | **Line:** 268
**Signature:** `format_event(event) → dict[str, Any]`

Format a WatcherEvent into Discord message kwargs (content, view).

Returns a dict with:
  - content: str (the message text)
  - view: discord.ui.View | None (interactive buttons if applicable)

## Calls

- [[eos_ai-substrate-session_discord_bridge-py-_extract_options]]

## Called By

- [[eos_ai-substrate-session_discord_bridge-py-SessionDiscordBridge-on_watcher_event]]
