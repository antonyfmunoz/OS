---
type: codebase-class
file: eos_ai/channel.py
line: 70
generated: 2026-04-12
---

# Channel

**File:** [[eos_ai-channel-py]] | **Line:** 70

Abstract channel interface.
send(): outbound notification
send_approval_request(): outbound with approve/deny
is_available(): check if channel configured

## Inherits From

- `ABC`

## Inherited By

- [[eos_ai-channel-py-DiscordChannel]]
- [[eos_ai-channel-py-TelegramChannel]]
- [[eos_ai-channel-py-WebhookChannel]]
- [[eos_ai-channel-py-ConsoleChannel]]

## Methods

- [[eos_ai-channel-py-Channel-send]]`(message, thread_id) → bool` — 
- [[eos_ai-channel-py-Channel-send_approval_request]]`(title, body, request_id, auto_approve_after_seconds) → bool` — 
- [[eos_ai-channel-py-Channel-is_available]]`() → bool` — 
- [[eos_ai-channel-py-Channel-send_safe]]`(message) → bool` — Send with fallback to console on failure.
