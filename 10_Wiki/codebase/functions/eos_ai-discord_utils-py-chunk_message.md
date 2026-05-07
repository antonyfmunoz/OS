---
type: codebase-function
file: eos_ai/discord_utils.py
line: 22
generated: 2026-05-07
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
