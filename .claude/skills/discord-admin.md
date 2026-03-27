# Discord Admin — Best Practices

## When to use this skill
Any time you are creating, managing, or administering Discord server structure via the bot.

## Permissions required
The bot needs these permissions:
- `ADMINISTRATOR` (simplest)
- OR specific: `MANAGE_CHANNELS`, `MANAGE_ROLES`, `MANAGE_GUILD`,
  `MANAGE_WEBHOOKS`, `VIEW_CHANNEL`, `SEND_MESSAGES`, `CONNECT`, `SPEAK`

Enable in Discord Developer Portal:
- Message Content Intent
- Server Members Intent
- Presence Intent

## Library
EOS uses **py-cord 2.6.1** (`import discord`), not discord.py.
Commands use `@bot.command()` prefix pattern, not slash commands.

## Key patterns

### Find or create channel (idempotent)
```python
existing = discord.utils.get(guild.text_channels, name='channel-name')
if not existing:
    existing = await guild.create_text_channel(
        name='channel-name',
        topic='Channel description',
        category=category_object,
    )
```

### Find or create category
```python
category = discord.utils.get(guild.categories, name='CATEGORY NAME')
if not category:
    category = await guild.create_category('CATEGORY NAME')
```

### Create voice channel
```python
vc = await guild.create_voice_channel(name='Channel Name', category=category)
```

### Set channel permissions
```python
await channel.set_permissions(role, read_messages=True, send_messages=False)
```

### Create webhook
```python
webhook = await channel.create_webhook(name='EOS Notifications')
# Save webhook.url to .env
```

### Post to channel by name
```python
channel = discord.utils.get(guild.text_channels, name='channel-name')
if channel:
    await channel.send('message')
```

## EOS Discord structure
See `DiscordServerManager.setup_eos_structure()` in `discord_bot.py`.

Required channels (always create if missing):
```
🧠 EOS (category)
  general          — main conversation with DEX
  morning-brief    — daily intelligence
  decisions        — logged decisions
  wins             — closed deals
  agent-activity   — EOS agent log

⚡ Empyrean Creative (category)
  empyrean-strategy
  empyrean-pipeline
  empyrean-outreach

🏢 Lyfe Institute (category)
  lyfe-strategy
  lyfe-pipeline
  lyfe-outreach

👤 Personal Brand (category)
  brand-strategy
  content-ideas

🎙️ Voice (category)
  Founder's Office  (voice)
  War Room          (voice)
```

## Channel IDs
Channel IDs are stored in `13_Scripts/.env` as `DISCORD_CHANNEL_*` vars.
`CHANNEL_IDS` dict in `discord_bot.py` loads them at startup.
When new channels are created, save their IDs to `.env`.

## Async patterns
All Discord admin operations are `async`. Run from:
- `on_ready()` handler
- Bot commands (`!setup`)
- Background tasks via `bot.loop.create_task()`

## Stage-driven channel creation
When venture advances to Stage 2:
- Create `{company}-content` channel
- Create `{company}-systems` channel
- Announce in `#general`

When venture advances to Stage 3:
- Create `{company}-hiring` channel
- Create `{company}-operations` channel

## Self-validation requirement

Before ANY Discord post — run validation:

```python
from eos_ai.output_validator import validate_before_discord
content = validate_before_discord(content)
```

This catches and auto-fixes:
- Messages over 1800 chars → chunked automatically
- Empty messages → blocked
- Generic response patterns → flagged
- Missing footer signatures → flagged

The system validates itself. You do not need to catch these manually.
`discord_utils.post_to_webhook` already calls this automatically.
Only call it manually when posting via channel object without `discord_utils`.

## CRITICAL: Message length limits

Discord maximum: 2000 characters per message.
EOS standard: 1800 characters (200-char safety buffer).

NEVER post content longer than 1800 chars in a single message.
NEVER use arbitrary character slicing (`content[:1900]`).
NEVER write custom chunking logic in individual files.

ALWAYS use `discord_utils.py` for all Discord posting:
```python
from eos_ai.discord_utils import (
    chunk_message,    # split content at paragraph boundaries
    post_to_webhook,  # sync — for orchestrator, world_pulse, gws_scanner
    post_to_channel,  # sync wrapper for async channel.send — for non-bot contexts
)
```

`discord_utils.py` is the single source of truth for all Discord posting.
It splits on paragraph boundaries, never mid-sentence or mid-word.
It labels chunks automatically (Part 1/3, Part 2/3, etc.).
It prepends title to the first chunk when provided.

## Common mistakes
- Not checking if channel exists before creating (creates duplicates)
- Missing bot permissions in server settings
- Not saving webhook URLs to `.env`
- Running async Discord code from sync context (use `bot.loop.create_task()`)
- Using `commands.Bot` slash commands — EOS uses prefix commands (`!cmd`)
- Truncating content with `[:1900]` instead of using `discord_utils`
- Writing custom chunking logic outside `discord_utils.py`
