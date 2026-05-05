# Telegram Bot API — Creator-Level Best Practices
Source: https://core.telegram.org/bots/api
API Version: Bot API 7.x (latest stable)
SDK Version: raw HTTP (no SDK) + python-telegram-bot 21.x
Last Researched: 2026-04-03

---

# Tier 1 — Technical Mastery

## Authentication

Bot tokens are issued by @BotFather and follow the format `{bot_id}:{secret}`.
Every API request includes the token in the URL path:
`https://api.telegram.org/bot<token>/<method>`

- One active token per bot. Revoking via `/revoke` in BotFather invalidates
  the old token immediately.
- Token is equivalent to a password — anyone with it controls the bot.
- `getMe` is the canonical "am I authenticated" check — returns bot info
  or 401 Unauthorized.
- Bot tokens never expire unless explicitly revoked.
- No OAuth flow, no refresh tokens, no scopes — single static credential.

## Core Operations with Exact Signatures

### sendMessage
```
POST /bot{token}/sendMessage
{
  "chat_id": int | str,       # required — numeric ID or @channel_username
  "text": str,                 # required — 1-4096 characters
  "parse_mode": str,           # optional — "Markdown", "MarkdownV2", "HTML"
  "entities": [...],           # optional — pre-parsed formatting entities
  "reply_markup": {...},       # optional — InlineKeyboardMarkup, ReplyKeyboardMarkup, etc.
  "disable_notification": bool,# optional — send silently
  "protect_content": bool,     # optional — prevent forwarding/saving
  "reply_parameters": {...},   # optional — reply to specific message
  "message_thread_id": int,    # optional — forum topic ID
  "link_preview_options": {...} # optional — control link previews
}
Returns: Message object with message_id, chat, date, text, entities
```

### getUpdates (long polling)
```
GET /bot{token}/getUpdates
{
  "offset": int,              # optional — ID of first update to return
  "limit": int,               # optional — 1-100, default 100
  "timeout": int,             # optional — long poll timeout in seconds (0-50, recommended 25-30)
  "allowed_updates": [str]    # optional — filter update types: ["message", "callback_query", ...]
}
Returns: Array of Update objects
```
Critical: pass `offset = last_update_id + 1` to acknowledge processed updates.
Without this, the same updates return on every call.

### setWebhook
```
POST /bot{token}/setWebhook
{
  "url": str,                 # required — HTTPS URL, ports 443/80/88/8443
  "certificate": InputFile,   # optional — self-signed cert public key
  "ip_address": str,          # optional — fixed IP for webhook
  "max_connections": int,     # optional — 1-100, default 40
  "allowed_updates": [str],   # optional — same filter as getUpdates
  "drop_pending_updates": bool,# optional — discard old updates
  "secret_token": str         # optional — 1-256 chars, sent as X-Telegram-Bot-Api-Secret-Token header
}
```

### sendPhoto / sendDocument / sendVoice
```
POST /bot{token}/sendPhoto
{
  "chat_id": int | str,       # required
  "photo": str | InputFile,   # required — file_id, URL, or multipart upload
  "caption": str,             # optional — 0-1024 characters
  "parse_mode": str,          # optional — applies to caption
}
```
Same pattern for sendDocument (up to 50 MB), sendVoice (OGG/OPUS),
sendVideo (up to 50 MB), sendAudio, sendAnimation.

### editMessageText
```
POST /bot{token}/editMessageText
{
  "chat_id": int | str,       # required if inline_message_id not given
  "message_id": int,          # required if inline_message_id not given
  "text": str,                # required — new text, 1-4096 chars
  "parse_mode": str,
  "reply_markup": {...}       # optional — new inline keyboard
}
```

### deleteMessage
```
POST /bot{token}/deleteMessage
{
  "chat_id": int | str,       # required
  "message_id": int           # required
}
```
Bots can delete their own messages anytime. Can delete others' messages
in groups if bot is admin with delete permission. Messages older than
48 hours in groups cannot be deleted by non-admins.

### answerCallbackQuery
```
POST /bot{token}/answerCallbackQuery
{
  "callback_query_id": str,   # required
  "text": str,                # optional — notification text (0-200 chars)
  "show_alert": bool,         # optional — show as alert popup vs toast
  "url": str,                 # optional — open URL
  "cache_time": int           # optional — seconds to cache result (default 0)
}
```
Must be called within ~30s of receiving callback_query or button shows
loading spinner indefinitely.

## Pagination Patterns

getUpdates uses offset-based pagination. There is no cursor or page token.
- First call: no offset (returns oldest unconfirmed updates)
- Subsequent calls: `offset = last_update_id + 1`
- `limit` controls batch size (1-100)
- Telegram stores unconfirmed updates for 24 hours, then drops them

For file downloads, `getFile` returns a `file_path` valid for 1 hour:
```
GET /bot{token}/getFile?file_id={file_id}
# Returns: {"file_path": "documents/file_0.pdf"}
# Download: https://api.telegram.org/file/bot{token}/{file_path}
```

## Rate Limits

### Per-chat limits
- **Private chats**: ~1 message per second to the same user
- **Group chats**: ~20 messages per minute to the same group
- **Channels**: ~20 messages per minute

### Global limits
- **Different chats**: ~30 messages per second across all chats
- **Bulk notifications**: For broadcasting to many users, Telegram recommends
  not exceeding 30 messages/second and spreading sends over time
- **getUpdates**: No rate limit on polling itself, but use long polling
  (timeout=25-30s) to avoid hammering the server

### 429 Too Many Requests
When rate limited, the response includes `retry_after` (seconds).
Respect it — repeated violations can get the bot temporarily banned.

```json
{
  "ok": false,
  "error_code": 429,
  "description": "Too Many Requests: retry after 35",
  "parameters": {"retry_after": 35}
}
```

### Inline queries
- Results cached server-side for `cache_time` seconds (default 300)
- 50 results max per answerInlineQuery call

## Error Codes and Recovery

| Code | Meaning | Recovery |
|------|---------|----------|
| 200  | Success | — |
| 400  | Bad Request — malformed params, invalid chat_id, text too long, bad parse_mode | Fix request. Check parse_mode escaping. |
| 401  | Unauthorized — invalid or revoked token | Re-check TELEGRAM_BOT_TOKEN. Re-issue via BotFather if revoked. |
| 403  | Forbidden — bot blocked by user, bot not in chat, insufficient permissions | User must unblock or re-/start. For groups, check admin perms. |
| 404  | Not Found — wrong method name or bot token format | Check URL construction. |
| 409  | Conflict — another getUpdates/webhook instance running | Only one poller per bot. Kill duplicate processes. |
| 429  | Too Many Requests — rate limited | Wait `retry_after` seconds, then retry. Implement exponential backoff. |
| 500  | Internal Server Error — Telegram's side | Retry after 1-5 seconds. Transient. |
| 502  | Bad Gateway — Telegram infrastructure issue | Retry after 5-10 seconds. |

### Common 400 errors
- `"Bad Request: can't parse entities"` — Markdown/MarkdownV2 syntax error.
  Unescaped special characters in dynamic content.
- `"Bad Request: message is too long"` — exceeded 4096 char limit.
- `"Bad Request: chat not found"` — chat_id doesn't exist or bot never
  received a message from that chat.
- `"Bad Request: message to edit not found"` — message_id invalid or
  message was deleted.

## SDK Idioms

EOS uses two approaches — both are valid for different contexts:

### Raw HTTP (notifications, one-shot sends)
```python
import requests
url = f"https://api.telegram.org/bot{token}/sendMessage"
resp = requests.post(url, json={
    "chat_id": chat_id,
    "text": text[:4096],
}, timeout=15)
if not resp.ok:
    error = resp.json()
    print(f"Telegram error {error['error_code']}: {error['description']}")
```
Used in: dm_monitor.py, kpi_tracker.py, overnight_scrape.py, calendly_webhook.py

### Raw HTTP with urllib (zero-dependency, channel.py)
```python
import urllib.parse, urllib.request
data = urllib.parse.urlencode({
    "chat_id": chat_id,
    "text": text[:4096],
    "parse_mode": "Markdown",
}).encode()
req = urllib.request.Request(
    f"https://api.telegram.org/bot{token}/sendMessage",
    data=data, method="POST",
)
with urllib.request.urlopen(req, timeout=5):
    pass
```
Used in: eos_ai/channel.py (TelegramChannel) — no requests dependency in core.

### python-telegram-bot library (full bot with handlers)
```python
from telegram.ext import ApplicationBuilder, CommandHandler
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start_handler))
app.run_polling()
```
Used in: telegram_control.py only. Owns the polling loop. No other service
should call getUpdates.

## Anti-Patterns

1. **Polling from multiple processes** — Only one process can getUpdates
   at a time. 409 Conflict otherwise. telegram_control.py owns polling.
2. **Not confirming updates** — Forgetting to increment offset causes
   infinite reprocessing of the same messages.
3. **Using Markdown for programmatic content** — Dynamic text with
   underscores, asterisks, brackets breaks parsing. Use HTML or strip
   special chars.
4. **Ignoring 429 retry_after** — Continuing to send after rate limit
   causes longer bans. Always sleep for `retry_after` seconds.
5. **Sending without truncation** — Messages over 4096 chars fail.
   Always `text[:4096]` or split into chunks.
6. **Blocking on Telegram sends in critical paths** — Use short timeouts
   (5-15s) and catch exceptions. A Telegram outage should not crash EOS.
7. **Logging full API URLs** — Token is in the URL. Never log request URLs
   without redacting the token.

## Data Model

### Update object (top-level incoming event)
```
Update {
  update_id: int              # unique, monotonically increasing
  message?: Message           # new message
  edited_message?: Message    # edited message
  callback_query?: CallbackQuery  # inline button press
  inline_query?: InlineQuery  # inline mode query
  channel_post?: Message      # channel message
  ...
}
```

### Message object
```
Message {
  message_id: int
  from?: User                 # sender (absent in channels)
  chat: Chat                  # conversation
  date: int                   # Unix timestamp
  text?: str                  # UTF-8 text, 0-4096 chars
  entities?: [MessageEntity]  # bold, italic, links, commands, etc.
  reply_to_message?: Message
  photo?: [PhotoSize]         # array of sizes
  document?: Document
  voice?: Voice
  reply_markup?: InlineKeyboardMarkup
}
```

### Chat object
```
Chat {
  id: int                     # unique identifier
  type: str                   # "private", "group", "supergroup", "channel"
  title?: str                 # group/channel title
  username?: str
  first_name?: str
}
```

### CallbackQuery (inline button press)
```
CallbackQuery {
  id: str                     # must pass to answerCallbackQuery
  from: User
  message?: Message           # the message with the button
  data?: str                  # 1-64 bytes callback_data
}
```

## Webhooks and Events

### Webhook setup
- URL must be HTTPS with valid certificate
- Allowed ports: 443, 80, 88, 8443
- Self-signed certs supported (upload public key)
- `secret_token` header for request verification
- Telegram retries failed webhook deliveries with increasing delays
- Max 100 concurrent connections (configurable via `max_connections`)

### Webhook vs polling tradeoffs
| Factor | Webhook | Long Polling |
|--------|---------|-------------|
| Latency | Instant | Up to `timeout` seconds |
| Infrastructure | Needs public HTTPS endpoint | No public endpoint needed |
| Reliability | Telegram retries on failure | Client controls retry |
| Complexity | TLS cert, firewall, endpoint | Simple loop |
| EOS choice | Not used | Used everywhere |

EOS uses long polling because the VPS is behind Tailscale (no public
endpoint). This is the correct choice for a private control layer.

### Update types for allowed_updates filter
`message`, `edited_message`, `channel_post`, `edited_channel_post`,
`callback_query`, `inline_query`, `chosen_inline_result`,
`shipping_query`, `pre_checkout_query`, `poll`, `poll_answer`,
`my_chat_member`, `chat_member`, `chat_join_request`

## Limits

| Resource | Limit |
|----------|-------|
| Message text | 4096 UTF-8 characters |
| Caption (photo/video/document) | 1024 characters |
| Callback data | 1-64 bytes |
| Inline query | 256 characters |
| answerInlineQuery results | 50 per call |
| File upload (sendDocument) | 50 MB |
| File download (getFile) | 20 MB |
| Photo upload | 10 MB |
| Photo max dimension | 10000px total (width + height) |
| Video upload | 50 MB |
| Voice/audio upload | 50 MB |
| Sticker file | 512 KB (static), 64 KB (animated) |
| Bot description | 512 characters |
| Bot short description | 120 characters |
| Inline keyboard buttons per row | 8 |
| Inline keyboard rows | No hard limit, but ~100 practical |
| Reply keyboard buttons per row | 12 |
| getUpdates limit parameter | 1-100 (default 100) |
| getUpdates timeout | 0-50 seconds |
| Webhook URL length | No documented limit |
| Bot commands list | 100 commands max |
| Command length | 1-32 characters, lowercase + digits + underscores |
| File ID validity | Guaranteed valid indefinitely for same bot |
| getFile download link | Valid for ~1 hour |

## Cost Model

Telegram Bot API is completely free. No per-message fees, no monthly
charges, no API key costs, no tier system.

- No rate limit tiers — same limits for all bots
- No premium API access
- File storage is free (Telegram hosts all media)
- No webhook delivery charges
- Only cost: your server infrastructure for running the bot

This is one of the most cost-effective messaging APIs available.
Telegram monetizes through Premium subscriptions and ads in channels,
not through bot API usage.

## Version Pinning

Telegram Bot API versions are additive — new methods and fields are
added but existing ones rarely change. There is no version parameter
in API calls. You always hit the latest version.

- Breaking changes are rare and announced months in advance
- Deprecated fields are kept for backward compatibility
- python-telegram-bot library versions: pin in requirements.txt
  (currently `python-telegram-bot[job-queue]>=21.0`)
- No API version negotiation — always latest
- Changelog: https://core.telegram.org/bots/api-changelog

---

# Tier 2 — Creator Intelligence

## Design Intent

Telegram Bot API was designed with a specific philosophy:
- **HTTP-first**: No persistent connections required. Any language that
  can make HTTP requests can build a bot. No SDK required.
- **Stateless server**: Telegram maintains all state (messages, files,
  user data). Your bot is a thin processing layer.
- **Simplicity over power**: Limited but reliable. No complex threading
  model, no connection pools, no session management.
- **Privacy-forward**: Bots cannot see messages in groups unless mentioned
  or privacy mode is disabled. Cannot initiate conversations.

The tradeoff: you get extreme simplicity and reliability at the cost of
real-time capabilities (no WebSocket, no streaming) and rich UI (no
custom components, limited to keyboards and inline buttons).

For EOS, this is ideal: the founder sends commands, the system responds.
No complex UI needed. The simplicity means fewer failure modes.

## Problem-Solution Map

| Problem | Solution |
|---------|----------|
| Send notification to founder | `sendMessage` with chat_id from env |
| Receive commands from phone | `getUpdates` long polling or CommandHandler |
| Approval workflow | `sendMessage` with text-based approve/deny codes |
| 2FA code relay | Poll `getUpdates`, regex match 6-digit code |
| Long message content | Split at 4096 chars or send as document |
| Rich formatting | Use HTML parse_mode for reliability |
| Button interactions | InlineKeyboardMarkup + answerCallbackQuery |
| Scheduled messages | python-telegram-bot JobQueue with run_daily |
| Silent notifications | `disable_notification: true` |
| Send files/images | sendDocument/sendPhoto with file path or URL |
| Track message delivery | Check response for message_id (no read receipts) |
| Error recovery | Check `ok` field, handle `error_code`, respect `retry_after` |

### Hidden capabilities
- **getFile + download** — retrieve voice messages sent by founder for STT
- **sendChatAction** — show "typing..." indicator during long operations
- **forwardMessage** — relay messages between chats without re-sending
- **copyMessage** — forward without the "forwarded from" header
- **exportChatInviteLink** — generate invite links for community management
- **setChatMenuButton** — custom menu button for the bot
- **setMyCommands** — register command autocomplete per-scope (per-chat,
  per-language)

## Operational Behavior

### Long polling edge cases
- If your server crashes mid-poll, unconfirmed updates stay in the queue
  for 24 hours. On restart, you'll reprocess them unless you store the
  last offset.
- Network timeouts during long poll are normal — just retry.
- If Telegram's servers are slow, getUpdates may return after the timeout
  with an empty result. This is not an error.
- Running `getUpdates` with offset=-1 and limit=1 is the canonical way
  to skip all pending updates and get only the latest.

### Message ordering
- Updates arrive in order per-chat, but callback_queries from inline
  keyboards may arrive out of order relative to messages.
- In groups with many members, update_id ordering is global, not per-user.

### File handling
- Telegram compresses photos (max 10MB, max 10000px total dimensions).
  For uncompressed images, send as document.
- file_id is stable for the same file in the same bot. Different bots
  get different file_ids for the same file.
- Downloading files requires a two-step process: getFile for the path,
  then HTTP GET on the file URL.

### Webhook reliability
- Telegram retries webhook deliveries with exponential backoff up to
  about 1 hour, then gives up.
- If your webhook consistently fails, Telegram may disable it.
- Check webhook status with `getWebhookInfo` — shows pending_update_count,
  last_error_date, last_error_message.

## Ecosystem Position

Telegram Bot API sits in a unique position:
- **Simpler than Discord bots** — no gateway WebSocket, no intents system,
  no sharding. Pure HTTP request-response.
- **More capable than SMS/email** — inline keyboards, media, formatting,
  real-time delivery.
- **Less capable than Slack apps** — no blocks/modals system, no workspace
  management, limited rich UI.
- **More private than WhatsApp Business** — no phone number required for
  bots, no read receipts exposed to bots.

### Composition with other tools
In EOS, Telegram is the **command and notification layer**:
- Telegram receives commands → cognitive_loop processes → Telegram sends response
- External events (Calendly booking, DM detection, scrape completion) →
  notification sent via Telegram
- Authority engine → approval request via Telegram → founder responds
- Morning briefing → scheduled via JobQueue → sent to Telegram

Telegram does NOT handle:
- Community interaction (Discord)
- Content delivery (Notion)
- Lead management (CRM pipeline)
- AI processing (model_router)

## Trajectory

Telegram Bot API evolution direction:
- **Bot API 7.x** (current) — added reactions, message effects, boosts,
  business accounts, gifts, star payments
- **Telegram Stars** — in-bot payments via Telegram's digital currency.
  createInvoiceLink, sendInvoice for monetization.
- **Telegram Mini Apps** (WebApps) — full web applications embedded in
  Telegram. Could replace a native app for EOS mobile interface.
- **Business accounts** — bots can now manage business chats, set greeting
  messages, away messages. Potential for Initiate Arena customer support.
- **Telegram Premium features** — bots can check if users have Premium,
  send larger files (4GB for Premium users).

### Future EOS opportunities
- Mini Apps for a mobile dashboard (KPIs, pipeline, approvals)
- Telegram Stars for Initiate Arena payments
- Business account integration for customer support
- Inline mode for quick lookups from any chat

## Conceptual Model

### The bot as a thin HTTP service
```
Founder's phone
    ↓ (sends message)
Telegram servers (stores message, creates Update)
    ↓ (getUpdates response or webhook POST)
EOS telegram_control.py (processes command)
    ↓ (calls cognitive_loop, KPI tracker, etc.)
EOS telegram_control.py (formats response)
    ↓ (sendMessage POST)
Telegram servers (delivers to founder)
    ↓
Founder's phone (notification)
```

### Update lifecycle
1. User sends message → Telegram creates Update with unique update_id
2. Bot polls getUpdates → receives array of unconfirmed Updates
3. Bot processes each Update, performs actions
4. Bot calls getUpdates with offset=last_id+1 → confirms processed Updates
5. Confirmed Updates are removed from queue

### Message types hierarchy
```
Text message     → message.text
Photo            → message.photo (array of PhotoSize)
Document         → message.document
Voice            → message.voice
Video            → message.video
Location         → message.location
Contact          → message.contact
Command          → message.text starting with / + message.entities[0].type == "bot_command"
Button press     → callback_query (separate from message)
Inline query     → inline_query (separate from message)
```

### Solution recipes for common EOS patterns

**Pattern: Notification with retry**
```python
import time, requests

def notify(token, chat_id, text, max_retries=3):
    for attempt in range(max_retries):
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text[:4096]},
            timeout=15,
        )
        if resp.ok:
            return True
        data = resp.json()
        if data.get("error_code") == 429:
            time.sleep(data.get("parameters", {}).get("retry_after", 30))
            continue
        break
    return False
```

**Pattern: Send with inline keyboard**
```python
import json, requests

def send_with_buttons(token, chat_id, text, buttons):
    """buttons: list of (text, callback_data) tuples"""
    keyboard = {"inline_keyboard": [
        [{"text": t, "callback_data": d}] for t, d in buttons
    ]}
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": text[:4096],
            "reply_markup": keyboard,
        },
        timeout=15,
    )
```

## Industry Expert

### Telegram bot best practices from production operators

1. **Always use HTML parse_mode** when generating messages programmatically.
   Markdown and MarkdownV2 are designed for human-authored messages where
   you control every character. HTML is designed for templates.

2. **Store file_ids** instead of re-uploading. If you send the same image
   repeatedly, save the file_id from the first response and reuse it.
   Telegram serves cached files instantly.

3. **Use sendChatAction** for operations taking >2 seconds. Showing
   "typing..." prevents the user from thinking the bot is dead.

4. **Implement graceful shutdown**: on SIGTERM, stop the polling loop,
   finish processing current updates, then exit. python-telegram-bot
   handles this with `app.run_polling(stop_signals=[SIGINT, SIGTERM])`.

5. **For high-throughput bots** (not EOS's case), use webhook mode with
   async frameworks (aiohttp, FastAPI). Long polling has inherent latency.

6. **Message editing for progress**: Instead of sending multiple messages,
   send one and use editMessageText to update it. Cleaner UX for
   long-running operations.

7. **MTProto vs Bot API**: The Bot API is an HTTP wrapper around Telegram's
   native MTProto protocol. MTProto gives raw access (user accounts, full
   chat history, real-time events) but is complex and TOS-sensitive for
   automation. Bot API is the sanctioned path. EOS correctly uses Bot API.

8. **Telegram's infrastructure**: Telegram operates distributed data
   centers (DC1-DC5). Bot API requests are routed to the DC where the
   chat lives. This means latency varies by user geography. For a single
   founder (EOS's case), this is irrelevant.

9. **Local Bot API Server**: Telegram offers a self-hosted Bot API server
   for high-volume bots (>100M users). Removes file size limits, gives
   direct file access. Overkill for EOS but worth knowing exists.

10. **Flood control strategy**: For bulk sends (broadcasting to many users),
    implement a message queue with 30 msg/sec rate limiting. In EOS this
    is irrelevant — single recipient — but matters for future Initiate
    Arena notifications to multiple players.

---

## EOS Usage Patterns

### Current architecture
- **telegram_control.py** — owns the polling loop via python-telegram-bot.
  All command handlers and natural language routing live here.
- **Notification scripts** — fire-and-forget sendMessage via requests.post.
  Used in dm_monitor, kpi_tracker, overnight_scrape, calendly_webhook.
- **channel.py** — TelegramChannel class for proactive_engine and
  authority_engine. Uses urllib (no requests dependency in eos_ai core).

### Key env vars
```
TELEGRAM_BOT_TOKEN   — bot credential from BotFather
TELEGRAM_CHAT_ID     — founder's chat ID (numeric)
```

### Scheduled jobs
| Job | Time | Source |
|-----|------|--------|
| Morning briefing | 06:00 | telegram_control.py |
| EOD report | 18:00 | telegram_control.py |
| Midnight snapshot | 23:59 | telegram_control.py |
| Signal scan | 12:00, 18:00 | telegram_control.py |

## Gotchas

1. **409 Conflict on getUpdates** — telegram_control.py and dm_monitor.py
   both use getUpdates. Only one can poll at a time. dm_monitor uses a
   short one-shot poll for 2FA codes; telegram_control owns the long-running
   poll. If both run simultaneously, one gets 409.

2. **Markdown escaping in channel.py** — The TelegramChannel uses
   parse_mode=Markdown. Dynamic content with underscores (common in
   Python variable names, URLs) breaks parsing. Should migrate to HTML.

3. **4096 character truncation** — channel.py truncates with `text[:4096]`.
   This can cut mid-word or mid-emoji (multi-byte). A smarter split
   at sentence boundaries would be better for long messages.

4. **Timeout mismatch risk** — dm_monitor uses requests timeout=10 for
   initial getUpdates but timeout=35 for long poll (timeout param=30).
   The 5-second margin is correct. If someone reduces it, the request
   will time out before Telegram responds.

5. **No error handling in kpi_tracker send_telegram** — The function does
   not catch exceptions. A Telegram outage will crash the KPI report.
