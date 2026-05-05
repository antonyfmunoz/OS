---
type: codebase-function
file: eos_ai/discord_utils.py
line: 145
generated: 2026-04-12
---

# post_to_channel

**File:** [[eos_ai-discord_utils-py]] | **Line:** 145
**Signature:** `post_to_channel(channel, content, title) → None`

Post content to a Discord channel object with paragraph-aware chunking.

Used inside the bot (not webhook). Schedules sends as an async task
when the event loop is running, or runs synchronously otherwise.

## Calls

- [[eos_ai-discord_utils-py-chunk_message]]

## Called By

- [[services-discord_bot-py-post_morning_brief]]
- [[services-discord_bot-py-post_outreach_alert]]
- [[services-discord_bot-py-post_win]]
