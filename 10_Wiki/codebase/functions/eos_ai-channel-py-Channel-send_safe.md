---
type: codebase-function
file: eos_ai/channel.py
line: 97
generated: 2026-04-12
---

# Channel.send_safe

**File:** [[eos_ai-channel-py]] | **Line:** 97
**Signature:** `send_safe(message) → bool`

**Class:** [[eos_ai-channel-py-Channel]]

Send with fallback to console on failure.

## Calls

- [[eos_ai-channel-py-Channel-is_available]]
- [[eos_ai-channel-py-Channel-send]]
- [[eos_ai-channel-py-ConsoleChannel-is_available]]
- [[eos_ai-channel-py-ConsoleChannel-send]]
- [[eos_ai-channel-py-DiscordChannel-is_available]]
- [[eos_ai-channel-py-DiscordChannel-send]]
- [[eos_ai-channel-py-TelegramChannel-is_available]]
- [[eos_ai-channel-py-TelegramChannel-send]]
- [[eos_ai-channel-py-WebhookChannel-is_available]]
- [[eos_ai-channel-py-WebhookChannel-send]]

## Called By

- [[eos_ai-channel-py-ChannelRouter-notify]]
