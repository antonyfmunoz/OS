---
type: codebase-class
file: services/discord_bot.py
line: 1674
generated: 2026-04-12
---

# DiscordServerManager

**File:** [[services-discord_bot-py]] | **Line:** 1674

Idempotent Discord server structure manager.
Creates channels and categories only if they don't already exist.
Called on bot ready and via !setup command.

## Methods

- [[services-discord_bot-py-DiscordServerManager-__init__]]`(guild)` — 
- [[services-discord_bot-py-DiscordServerManager-ensure_category]]`(name) → discord.CategoryChannel` — Find or create a category.
- [[services-discord_bot-py-DiscordServerManager-ensure_channel]]`(name, category_name, topic, channel_type) → discord.abc.GuildChannel | None` — Find or create a channel. Returns channel object.
- [[services-discord_bot-py-DiscordServerManager-setup_eos_structure]]`() → list[str]` — Create full EOS Discord structure. Only creates what doesn't exist.
- [[services-discord_bot-py-DiscordServerManager-align_structure]]`() → None` — Enforce the canonical EOS channel layout.
- [[services-discord_bot-py-DiscordServerManager-update_for_stage_change]]`(company, new_stage) → list[str]` — Create stage-appropriate channels when a venture advances.
