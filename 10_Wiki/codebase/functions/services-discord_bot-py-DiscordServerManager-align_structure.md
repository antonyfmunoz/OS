---
type: codebase-function
file: services/discord_bot.py
line: 1729
generated: 2026-04-11
---

# DiscordServerManager.align_structure

**File:** [[services-discord_bot-py]] | **Line:** 1729
**Signature:** `align_structure() → None`

**Class:** [[services-discord_bot-py-DiscordServerManager]]

Enforce the canonical EOS channel layout.
Moves uncategorized channels into 🧠 EOS.
Removes redundant generic channels.
Safe to call on every startup.

## Called By

- [[services-discord_bot-py-_setup_server_structure]]
- [[services-discord_bot-py-cmd_align]]
- [[services-discord_bot-py-on_message]]
