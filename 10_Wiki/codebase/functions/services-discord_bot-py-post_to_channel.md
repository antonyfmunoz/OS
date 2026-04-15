---
type: codebase-function
file: services/discord_bot.py
line: 2986
generated: 2026-04-12
---

# post_to_channel

**File:** [[services-discord_bot-py]] | **Line:** 2986
**Signature:** `post_to_channel(channel_name, content) → bool`

Post content to a named channel by ID. Returns True if sent.

## Calls

- [[eos_ai-discord_utils-py-chunk_message]]

## Called By

- [[services-discord_bot-py-post_morning_brief]]
- [[services-discord_bot-py-post_outreach_alert]]
- [[services-discord_bot-py-post_win]]
