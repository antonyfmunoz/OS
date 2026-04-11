---
type: codebase-function
file: eos_ai/discord_utils.py
line: 88
generated: 2026-04-11
---

# post_to_webhook

**File:** [[eos_ai-discord_utils-py]] | **Line:** 88
**Signature:** `post_to_webhook(content, title, username, webhook_url) → bool`

Post content to a Discord webhook with paragraph-aware chunking.

Handles splitting automatically — callers never truncate manually.
Returns True if all chunks posted successfully.

## Calls

- [[eos_ai-discord_utils-py-chunk_message]]
