---
type: codebase-function
file: services/discord_bot.py
line: 1677
generated: 2026-04-11
---

# DiscordServerManager.setup_eos_structure

**File:** [[services-discord_bot-py]] | **Line:** 1677
**Signature:** `setup_eos_structure() → list[str]`

**Class:** [[services-discord_bot-py-DiscordServerManager]]

Create full EOS Discord structure. Only creates what doesn't exist.

## Calls

- [[services-discord_bot-py-DiscordServerManager-ensure_channel]]

## Called By

- [[services-discord_bot-py-_setup_server_structure]]
- [[services-discord_bot-py-cmd_setup]]
- [[services-discord_bot-py-on_message]]
