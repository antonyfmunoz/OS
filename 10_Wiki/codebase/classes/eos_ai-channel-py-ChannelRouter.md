---
type: codebase-class
file: eos_ai/channel.py
line: 297
generated: 2026-04-12
---

# ChannelRouter

**File:** [[eos_ai-channel-py]] | **Line:** 297

Single control plane for all channels.

Usage:
    router = ChannelRouter.from_env()
    router.notify("Agent task complete")
...

## Methods

- [[eos_ai-channel-py-ChannelRouter-__init__]]`(channels)` — 
- [[eos_ai-channel-py-ChannelRouter-_find_primary]]`() → Channel` — 
- [[eos_ai-channel-py-ChannelRouter-from_env]]`() → 'ChannelRouter'` — Build router from environment variables.
- [[eos_ai-channel-py-ChannelRouter-notify]]`(message, all_channels) → bool` — Send notification. Cascades through channels on failure.
- [[eos_ai-channel-py-ChannelRouter-request_approval]]`(title, body, request_id, is_safe) → bool` — Send permission approval request. Cascades on failure.
- [[eos_ai-channel-py-ChannelRouter-get_status]]`() → dict` — Return status of all channels.
