---
type: codebase-function
file: services/discord_bot.py
line: 1692
generated: 2026-04-12
---

# DiscordServerManager.ensure_channel

**File:** [[services-discord_bot-py]] | **Line:** 1692
**Signature:** `ensure_channel(name, category_name, topic, channel_type) → discord.abc.GuildChannel | None`

**Class:** [[services-discord_bot-py-DiscordServerManager]]

Find or create a channel. Returns channel object.

## Calls

- [[services-discord_bot-py-DiscordServerManager-ensure_category]]

## Called By

- [[services-discord_bot-py-DiscordServerManager-setup_eos_structure]]
- [[services-discord_bot-py-DiscordServerManager-update_for_stage_change]]
