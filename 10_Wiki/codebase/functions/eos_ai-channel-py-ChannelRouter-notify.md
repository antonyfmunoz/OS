---
type: codebase-function
file: eos_ai/channel.py
line: 389
generated: 2026-05-07
---

# ChannelRouter.notify

**File:** [[eos_ai-channel-py]] | **Line:** 389
**Signature:** `notify(message, all_channels) → bool`

**Class:** [[eos_ai-channel-py-ChannelRouter]]

Send notification. Cascades through channels on failure.

## Calls

- [[eos_ai-channel-py-Channel-is_available]]
- [[eos_ai-channel-py-Channel-send]]
- [[eos_ai-channel-py-Channel-send_safe]]
- [[eos_ai-channel-py-ConsoleChannel-is_available]]
- [[eos_ai-channel-py-ConsoleChannel-send]]
- [[eos_ai-channel-py-DiscordChannel-is_available]]
- [[eos_ai-channel-py-DiscordChannel-send]]
- [[eos_ai-channel-py-TelegramChannel-is_available]]
- [[eos_ai-channel-py-TelegramChannel-send]]
- [[eos_ai-channel-py-WebhookChannel-is_available]]
- [[eos_ai-channel-py-WebhookChannel-send]]

## Called By

- [[eos_ai-channel-py-ChannelRouter-request_approval]]
