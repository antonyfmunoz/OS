---
type: codebase-function
file: eos_ai/substrate/session_discord_bridge.py
line: 373
generated: 2026-05-07
---

# SessionDiscordBridge.on_watcher_event

**File:** [[eos_ai-substrate-session_discord_bridge-py]] | **Line:** 373
**Signature:** `on_watcher_event(event) → None`

**Class:** [[eos_ai-substrate-session_discord_bridge-py-SessionDiscordBridge]]

Callback for SessionWatcher — formats and sends Discord notification.

This runs in the watcher's daemon thread, so we schedule the async
send onto the bot's event loop.

## Calls

- [[eos_ai-substrate-session_discord_bridge-py-SessionDiscordBridge-_get_channel]]
- [[eos_ai-substrate-session_discord_bridge-py-SessionDiscordBridge-_send_notification]]
- [[eos_ai-substrate-session_discord_bridge-py-format_event]]
