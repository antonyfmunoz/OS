---
type: codebase-function
file: eos_ai/channel.py
line: 417
generated: 2026-04-12
---

# ChannelRouter.request_approval

**File:** [[eos_ai-channel-py]] | **Line:** 417
**Signature:** `request_approval(title, body, request_id, is_safe) → bool`

**Class:** [[eos_ai-channel-py-ChannelRouter]]

Send permission approval request. Cascades on failure.

## Calls

- [[eos_ai-channel-py-Channel-is_available]]
- [[eos_ai-channel-py-Channel-send_approval_request]]
- [[eos_ai-channel-py-ChannelRouter-notify]]
- [[eos_ai-channel-py-ConsoleChannel-is_available]]
- [[eos_ai-channel-py-ConsoleChannel-send_approval_request]]
- [[eos_ai-channel-py-DiscordChannel-is_available]]
- [[eos_ai-channel-py-DiscordChannel-send_approval_request]]
- [[eos_ai-channel-py-TelegramChannel-is_available]]
- [[eos_ai-channel-py-TelegramChannel-send_approval_request]]
- [[eos_ai-channel-py-WebhookChannel-is_available]]
- [[eos_ai-channel-py-WebhookChannel-send_approval_request]]
