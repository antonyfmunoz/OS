---
name: discord
description: "Use when building or modifying Discord bot features, sending messages to Discord channels, configuring intents or permissions, or debugging Discord connectivity issues."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://discord.com/developers/docs/intro"
last_researched: "2026-04-03"
instantiated_from: templates/tools/_template/
api_version: "10"
sdk_version: "py-cord 2.7.1"
speed_category: medium
trigger: both
effort: medium
context: fork
---

# Tool: Discord (py-cord)

## What This Tool Does

Discord API v10 provides real-time messaging, voice, slash commands, and webhook-based
notifications for bot applications. EOS uses py-cord (Pycord) 2.7.1, a maintained fork
of discord.py that adds first-class slash command support, UI components (buttons, modals,
selects), and voice recording sinks.

Core capabilities used by EOS:
- **Text channels** — bidirectional: inbound messages routed through EOS gateway,
  outbound agent responses posted back
- **Voice channels** — auto-join founder, silence-detecting audio capture, Groq STT
- **Webhooks** — 15+ scripts post notifications (briefs, pipeline updates, alerts)
- **Slash commands** — not currently used but supported by py-cord
- **Embeds** — structured rich messages with fields, colors, footers
- **Views/Buttons** — interactive UI components for confirmations and selections

## EOS Integration

### Primary service
`services/discord_bot.py` — DEX conversational layer. Runs as `os-discord` Docker container.

### Bot-side patterns
- `commands.Bot(command_prefix="!", intents=intents)` — prefix commands + events
- `@bot.event async def on_message()` — all inbound text routed through intent classification
- `SilenceDetectingSink` — custom voice recording with utterance detection
- `CHANNEL_IDS` dict — 13 named channels mapped to snowflake IDs
- `CHANNEL_MAP` dict — channel name to intent routing hint
- `FOUNDER_ID` — auto-join voice, priority routing

### Webhook-side patterns (15+ scripts)
All outbound notifications go through `eos_ai/discord_utils.py`:
- `post_to_webhook(content, title, username, webhook_url)` — chunked webhook posting
- `post_to_channel(channel, content, title)` — bot-side chunked channel posting
- `chunk_message(content, title)` — paragraph-aware splitting at 1800 chars (200-char safety buffer)
- Env var: `DISCORD_BRIEF_WEBHOOK` — default webhook URL

Scripts using webhooks: `morning_intel.py`, `portfolio_brief.py`, `weekly_review.py`,
`eod_sync.py`, `midday_checkin.py`, `inbox_gps_afternoon.py`, `call_prep.py`,
`day_reminder.py`, `deadline_monitor.py`, `noshow_detector.py`, `relationship_nurture.py`,
`waiting_on_checker.py`, `calendar_invite_handler.py`, `agent_task_executor.py`,
`nightly_maintenance.sh`, `weekly_review.sh`.

### Channel architecture
`eos_ai/channel.py` — normalized channel adapter pattern. Discord is priority 1.
Inbound: Discord message -> EOS agent runs. Outbound: EOS agent completes -> Discord post.

## Authentication

### Bot token auth
1. Discord Developer Portal -> Applications -> New Application
2. Bot section -> Add Bot -> copy token
3. Store as `DISCORD_BOT_TOKEN` in `services/.env`
4. Never commit tokens. Never log tokens.

### Required intents (Developer Portal + code)
All four privileged intents must be enabled in the Developer Portal AND in code:
```python
intents = discord.Intents.default()
intents.message_content = True   # 1 << 15 — PRIVILEGED: read message text
intents.voice_states = True      # 1 << 7  — required for voice connection
intents.presences = True         # 1 << 8  — PRIVILEGED: member status
intents.members = True           # 1 << 1  — PRIVILEGED: member events
```
`Intents.default()` enables everything EXCEPT `presences`, `members`, and `message_content`.
Bots in 100+ guilds need Discord verification to use privileged intents.

### Required bot permissions
Send Messages, Read Message History, Add Reactions, Connect (voice),
Speak (voice), Use Slash Commands, Embed Links, Attach Files.

### Env vars
```
DISCORD_BOT_TOKEN=       # Bot token from developer portal
FOUNDER_DISCORD_ID=      # Snowflake ID of the founder's Discord account
DISCORD_BRIEF_WEBHOOK=   # Webhook URL for morning brief channel
```

## Quick Reference

### Send a message to a channel
```python
channel = bot.get_channel(CHANNEL_IDS["morning-brief"])
await channel.send("Good morning.")
```

### Send with chunking (messages over 2000 chars)
```python
from eos_ai.discord_utils import chunk_message
chunks = chunk_message(long_text, title="Daily Brief")
for chunk in chunks:
    await channel.send(chunk)
```

### Post via webhook (from any script, no bot instance needed)
```python
from eos_ai.discord_utils import post_to_webhook
post_to_webhook(
    content="Pipeline update: 3 new leads",
    title="Sales Alert",
    username="DEX",
    webhook_url=os.getenv("DISCORD_BRIEF_WEBHOOK"),
)
```

### Create an embed
```python
embed = discord.Embed(
    title="Morning Brief",
    description="Your daily overview",
    color=discord.Color.blue(),  # int or Color object
)
embed.add_field(name="Pipeline", value="3 active leads", inline=True)
embed.set_footer(text="Generated by EOS")
await channel.send(embed=embed)
```

### Register a slash command (py-cord style)
```python
@bot.slash_command(name="status", description="Get EOS status")
async def status(ctx: discord.ApplicationContext):
    await ctx.respond("All systems operational.")
```

### Voice connection
```python
vc = await voice_channel.connect()
# Start recording with custom sink
sink = SilenceDetectingSink(on_utterance=callback)
vc.start_recording(sink, finished_callback)
```

### Button/View interaction
```python
class ConfirmView(discord.ui.View):
    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def approve(self, button, interaction):
        await interaction.response.send_message("Approved.")

await channel.send("Confirm?", view=ConfirmView())
```

## Conceptual Model

```
Discord API v10
  |
  +-- Gateway (WebSocket) --- real-time events
  |     |-- Intents filter which events you receive
  |     |-- Heartbeat keeps connection alive (interval from HELLO)
  |     |-- Resume reconnects without re-identifying
  |     +-- Sharding splits large bots across connections
  |
  +-- REST API --- CRUD operations
  |     |-- Rate limited per-route with bucket headers
  |     |-- 50 requests/second global limit
  |     +-- Webhooks bypass bot auth (token-free posting)
  |
  +-- py-cord 2.7.1 (SDK layer)
        |-- commands.Bot — prefix commands + event handlers
        |-- discord.slash_command — application commands
        |-- discord.ui.View — buttons, selects, modals
        |-- discord.VoiceClient — voice connections + recording
        +-- discord.Embed — rich formatted messages
```

See references/best_practices.md for rate limits, error codes, and anti-patterns.

## Gotchas

### Voice WebSocket crash (_MissingSentinel)
py-cord voice connections throw `_MissingSentinel` / `poll_voice_ws` exceptions
that bypass `on_error`. EOS handles this at the asyncio event loop level with a
custom `_handle_task_exception` handler that silences these specific errors.
Never remove this handler.

### Voice connect before on_ready
`on_voice_state_update` fires during gateway resume before the bot is fully initialized.
Connecting to voice in that window causes the _MissingSentinel crash.
EOS guards with a `_bot_ready` flag set in `on_ready`.

### Message content intent required for on_message
Without `message_content=True` in intents AND enabled in Developer Portal,
`message.content` is empty string for guild messages. The bot appears to work
but silently receives no text. This is the most common new-bot debugging issue.

### 2000 character message limit
Discord hard-caps messages at 2000 characters. Sending longer text returns 400.
Always use `chunk_message()` from `discord_utils.py`. The EOS standard is 1800 chars
(200-char safety buffer for part labels and titles).

### Webhook rate limits
Webhooks share rate limits: 5 requests per 2 seconds per webhook.
Multiple EOS scripts posting simultaneously can hit 429s.
`post_to_webhook()` includes `time.sleep(0.5)` between chunks.

### Intents.default() excludes privileged intents
`Intents.default()` does NOT include `members`, `presences`, or `message_content`.
You must explicitly enable each one. Forgetting any one silently breaks functionality
without obvious errors.

### Gateway close code 4014: Disallowed intents
If you request a privileged intent in code but haven't enabled it in the Developer Portal,
the gateway immediately closes with code 4014. The bot appears to start then instantly dies.

### Embed field limits
Embed title: 256 chars. Description: 4096 chars. Fields: 25 max. Field name: 256 chars.
Field value: 1024 chars. Footer: 2048 chars. Total embed: 6000 chars.
Exceeding any limit returns 400.

### Bot token in env
The `DISCORD_BOT_TOKEN` lives in `services/.env`, not `eos_ai/.env`.
Both env files are loaded by discord_bot.py. Token lookups fail if you put it
in the wrong env file and load order changes.
