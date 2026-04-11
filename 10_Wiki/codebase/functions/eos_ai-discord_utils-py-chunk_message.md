---
type: codebase-function
file: eos_ai/discord_utils.py
line: 22
generated: 2026-04-11
---

# chunk_message

**File:** [[eos_ai-discord_utils-py]] | **Line:** 22
**Signature:** `chunk_message(content, title) → list[str]`

Split content at paragraph boundaries.

Never splits mid-sentence or mid-word.
Each chunk stays under DISCORD_MAX_CHARS.
Adds part labels when more than one chunk.
...

## Called By

- [[eos_ai-discord_utils-py-post_to_channel]]
- [[eos_ai-discord_utils-py-post_to_webhook]]
- [[services-discord_bot-py-_listen_loop]]
- [[services-discord_bot-py-_send_response]]
- [[services-discord_bot-py-cmd_approve]]
- [[services-discord_bot-py-cmd_draft]]
- [[services-discord_bot-py-cmd_report]]
- [[services-discord_bot-py-cmd_status]]
- [[services-discord_bot-py-cmd_sync]]
- [[services-discord_bot-py-cmd_verify_inbox]]
- [[services-discord_bot-py-on_message]]
- [[services-discord_bot-py-post_to_channel]]
