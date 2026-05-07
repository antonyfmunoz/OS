---
type: codebase-class
file: core/action_system/notifier.py
line: 59
generated: 2026-05-07
---

# DiscordNotifier

**File:** [[core-action_system-notifier-py]] | **Line:** 59

Best-effort Discord webhook notifier.

Reads DISCORD_APPROVAL_WEBHOOK_URL from the environment. If unset or
the POST fails, returns {"ok": False, "reason": ...} but never raises.
Wrap alongside a FileNotifier in a MultiNotifier for durability.

## Methods

- [[core-action_system-notifier-py-DiscordNotifier-__init__]]`(webhook_url) → None` — 
- [[core-action_system-notifier-py-DiscordNotifier-notify]]`(action) → dict` — 
