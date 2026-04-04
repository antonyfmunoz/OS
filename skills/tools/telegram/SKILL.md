---
name: telegram
description: "Use when any agent sends notifications, receives commands, or interacts with the founder via Telegram Bot API."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://core.telegram.org/bots/api"
last_researched: "2026-04-03"
instantiated_from: templates/tools/_template/
api_version: "Bot API 7.x"
sdk_version: "raw HTTP (no SDK) + python-telegram-bot 21.x"
speed_category: stable
---

# Tool: Telegram Bot API

## What This Tool Does

Telegram Bot API is an HTTP-based interface for building bots on the Telegram
messaging platform. Bots can send and receive messages, photos, documents,
voice notes, and inline keyboards. They support both long polling (getUpdates)
and webhook-based update delivery.

Key capabilities used in EOS:
- **sendMessage** — text notifications with Markdown/HTML formatting
- **getUpdates** — long polling for incoming commands and 2FA codes
- **Inline keyboards** — approval/deny buttons for authority engine
- **Scheduled messages** — morning briefings, EOD reports, signal scans
- **Command handlers** — /brief, /pipeline, /kpi, natural language routing

## EOS Integration

### Primary service: telegram_control.py
Uses **python-telegram-bot** library (ApplicationBuilder, CommandHandler,
MessageHandler). Handles:
- Command dispatch (/brief, /pipeline, /kpi, /costs, /voice, /meeting)
- Natural language message routing through cognitive_loop
- Scheduled jobs via JobQueue (6am briefing, 6pm EOD, midnight snapshot,
  12pm/6pm signal scans)
- Voice/meeting session management
- Per-chat message ordering via asyncio.Lock

### Notification scripts (raw HTTP)
These use `requests.post` to `api.telegram.org/bot{token}/sendMessage`:
- **dm_monitor.py** — Instagram DM alerts, 2FA code polling via getUpdates
- **kpi_tracker.py** — EOD KPI reports
- **overnight_scrape.py** — scrape completion summaries
- **calendly_webhook.py** — booking notifications
- **apify_scraper.py** — scrape result notifications

### Core AI layer
- **eos_ai/channel.py** — TelegramChannel class using urllib.request (no
  external dependency). Used by proactive_engine and authority_engine for
  approval requests with inline-style text buttons.

### Environment variables
```
TELEGRAM_BOT_TOKEN   — from BotFather, format: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_CHAT_ID     — numeric chat ID for the founder's private chat
```
Both stored in `services/.env` and `eos_ai/.env`.

## Authentication

### Creating a bot
1. Message @BotFather on Telegram
2. Send `/newbot`, follow prompts for name and username (must end in `bot`)
3. BotFather returns the token — store as `TELEGRAM_BOT_TOKEN`

### Discovering chat ID
Send any message to your bot, then:
```bash
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getUpdates" | python3 -m json.tool
```
Look for `result[0].message.chat.id` — store as `TELEGRAM_CHAT_ID`.

### Token format
`{bot_id}:{secret}` — the bot_id portion is numeric, the secret is
alphanumeric with hyphens. Total length ~46 characters.

### Security
- Never commit tokens to git (always .env)
- Tokens can be revoked via BotFather `/revoke`
- Only one active token per bot at a time

## Quick Reference

### Send a message (raw HTTP — notification pattern)
```python
import requests, os

def send_telegram(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text[:4096]},
        timeout=15,
    )
```

### Send with Markdown formatting (channel.py pattern)
```python
import urllib.parse, urllib.request

def send_markdown(token: str, chat_id: str, text: str) -> bool:
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
        return True
```

### Long poll for updates (dm_monitor.py pattern)
```python
import requests

def poll_for_code(token: str, timeout: int = 120) -> str | None:
    """Poll getUpdates for a 6-digit code (2FA flow)."""
    # Get current offset to skip old messages
    resp = requests.get(
        f"https://api.telegram.org/bot{token}/getUpdates",
        params={"offset": -1, "limit": 1}, timeout=10,
    )
    offset = None
    if resp.ok:
        updates = resp.json().get("result", [])
        if updates:
            offset = updates[-1]["update_id"] + 1

    import time, re
    deadline = time.time() + timeout
    while time.time() < deadline:
        params = {"timeout": 30}
        if offset is not None:
            params["offset"] = offset
        resp = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params=params, timeout=35,  # > long poll timeout
        )
        if resp.ok:
            for update in resp.json().get("result", []):
                offset = update["update_id"] + 1
                text = update.get("message", {}).get("text", "").strip()
                if re.match(r'^\d{6}$', text):
                    return text
    return None
```

### python-telegram-bot command handler (telegram_control.py pattern)
```python
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, filters,
)

async def brief(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Morning briefing here...")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("brief", brief))
app.run_polling()
```

## Conceptual Model

### Updates
Every incoming event is an **Update** with a unique `update_id`. Contains
one of: `message`, `edited_message`, `callback_query`, `inline_query`, etc.
Updates are consumed via getUpdates (polling) or webhook (push).

### Messages
Messages have `chat` (where), `from` (who), `text` (what), optional
`reply_to_message`, `entities` (bold, links, commands), and media fields.

### Commands
Messages starting with `/` are bot commands. Telegram parses them into
`entities` with type `bot_command`. BotFather registers the command list
for autocomplete.

### Inline keyboards
`reply_markup` with `InlineKeyboardMarkup` attaches buttons below a message.
Each button has `text` (display) and `callback_data` (payload, max 64 bytes).
Pressing a button sends a `callback_query` update — must be answered with
`answerCallbackQuery` within ~30 seconds or the button shows a loading spinner.

### Parse modes
- **Markdown** — `*bold*`, `_italic_`, `` `code` ``, `[link](url)`.
  Fragile with special chars.
- **MarkdownV2** — same but requires escaping: `_*[]()~>#+-=|{}.!`
- **HTML** — `<b>`, `<i>`, `<code>`, `<a href="">`. Most reliable for
  programmatic use.

## Gotchas

### 1. Message length limit is 4096 characters
sendMessage silently truncates or errors if text exceeds 4096 UTF-8
characters. EOS already handles this in channel.py with `text[:4096]`.
For longer content, split into multiple messages.

### 2. Markdown parse mode is fragile
Unescaped `_`, `*`, `[`, `` ` `` in dynamic content breaks Markdown
parsing and the message fails with 400 Bad Request. Use HTML parse_mode
for programmatic messages, or strip/escape special chars. MarkdownV2
requires escaping 18 special characters.

### 3. getUpdates and webhooks are mutually exclusive
If a webhook is set, getUpdates returns an error. EOS uses polling
(getUpdates) exclusively. If something sets a webhook accidentally,
clear it: `deleteWebhook`.

### 4. Long poll timeout must be less than requests timeout
The `timeout` parameter in getUpdates tells Telegram how long to hold
the connection. Your HTTP client timeout must be higher (e.g., poll
timeout=30, requests timeout=35). dm_monitor.py does this correctly.

### 5. Rate limits are per-chat, not per-bot
~1 message/second to same chat, ~30 messages/second to different chats.
Group chats limited to ~20 messages/minute. Exceeding returns 429 with
`retry_after` seconds. No explicit global cap documented.

### 6. Bot cannot initiate conversations
A bot can only send messages to users who have started a conversation
with it first (sent /start or any message). Cannot cold-message users.

### 7. callback_data max is 64 bytes
Inline keyboard callback_data is limited to 1-64 bytes. Stuffing JSON
or long IDs requires truncation or mapping (EOS uses short_id = id[:8]).

### 8. Token in URL means HTTPS is mandatory
The bot token appears in every API URL. Always use HTTPS (which
api.telegram.org enforces). Never log full request URLs.

### 9. getUpdates offset must be previous + 1
If you don't confirm updates by passing `offset = last_update_id + 1`,
you'll reprocess the same updates on every poll. dm_monitor.py handles
this correctly.

### 10. Two Telegram interfaces in EOS — keep them separate
telegram_control.py uses python-telegram-bot (async, ApplicationBuilder).
All other scripts use raw `requests.post`. Do not mix — only one process
can poll getUpdates at a time. telegram_control.py owns polling; other
scripts are send-only.

See references/best_practices.md for full rate limits, error codes, and API details.
