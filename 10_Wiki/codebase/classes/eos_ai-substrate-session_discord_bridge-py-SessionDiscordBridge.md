---
type: codebase-class
file: eos_ai/substrate/session_discord_bridge.py
line: 333
generated: 2026-05-07
---

# SessionDiscordBridge

**File:** [[eos_ai-substrate-session_discord_bridge-py]] | **Line:** 333

Bridges SessionWatcher events to a Discord bot instance.

Call set_bot() once the discord bot is ready, then use on_watcher_event()
as the SessionWatcher callback.

## Methods

- [[eos_ai-substrate-session_discord_bridge-py-SessionDiscordBridge-__init__]]`() → None` — 
- [[eos_ai-substrate-session_discord_bridge-py-SessionDiscordBridge-set_bot]]`(bot) → None` — Register the discord bot instance. Call from on_ready.
- [[eos_ai-substrate-session_discord_bridge-py-SessionDiscordBridge-_get_channel]]`(session_name) → discord.abc.Messageable | None` — Get the Discord channel for a session (per-session or fallback).
- [[eos_ai-substrate-session_discord_bridge-py-SessionDiscordBridge-on_watcher_event]]`(event) → None` — Callback for SessionWatcher — formats and sends Discord notification.
- [[eos_ai-substrate-session_discord_bridge-py-SessionDiscordBridge-_send_notification]]`(formatted, channel) → None` — Send formatted notification to Discord channel.
- [[eos_ai-substrate-session_discord_bridge-py-SessionDiscordBridge-handle_answer_command]]`(session_name, answer_text) → str` — Handle !answer command — pipe text back into session.
