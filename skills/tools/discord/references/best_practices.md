# Discord — Creator-Level Best Practices
Source: https://discord.com/developers/docs/intro
API Version: 10
SDK Version: py-cord 2.7.1
Last Researched: 2026-04-03

---

# Tier 1 — Technical Mastery

## Authentication

### Bot token auth
Bot tokens follow the format: `MTk...` (base64-encoded user ID, timestamp, HMAC).
Passed as `Authorization: Bot <token>` header on REST, and in the IDENTIFY payload on Gateway.

```python
bot = commands.Bot(command_prefix="!", intents=intents)
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
```

### OAuth2
For user-auth flows (not used in EOS): Authorization Code Grant with scopes
(`bot`, `applications.commands`, `identify`, `guilds`).
Token endpoint: `POST https://discord.com/api/v10/oauth2/token`

### Webhook auth
Webhooks are token-free. The URL itself is the credential:
`https://discord.com/api/webhooks/{webhook.id}/{webhook.token}`
Anyone with the URL can post. Treat webhook URLs as secrets.

## Core Operations with Exact Signatures

### Bot/Client initialization (py-cord 2.7.1)
```python
commands.Bot(
    command_prefix: str | Callable,  # prefix for text commands
    intents: discord.Intents,        # required — no default
    help_command: HelpCommand | None = default,
    description: str = "",
    **options,  # max_messages (cache), heartbeat_timeout, etc.
)
```

### Sending messages
```python
# Channel.send
await channel.send(
    content: str = None,        # text content (max 2000 chars)
    embed: Embed = None,        # single embed
    embeds: list[Embed] = None, # up to 10 embeds
    file: File = None,          # single attachment
    files: list[File] = None,   # up to 10 files
    view: View = None,          # buttons/selects
    delete_after: float = None, # auto-delete seconds
    reference: Message = None,  # reply reference
)
```

### Embed constructor
```python
discord.Embed(
    title: str = None,           # max 256 chars
    description: str = None,     # max 4096 chars
    color: int | Color = None,   # sidebar color
    url: str = None,             # title hyperlink
    timestamp: datetime = None,  # footer timestamp
)
# Methods:
embed.add_field(name: str, value: str, inline: bool = True)  # max 25 fields
embed.set_footer(text: str, icon_url: str = None)            # max 2048 chars
embed.set_author(name: str, url: str = None, icon_url: str = None)
embed.set_image(url: str)    # large image below description
embed.set_thumbnail(url: str) # small image top-right
```

### Slash commands (py-cord native)
```python
@bot.slash_command(
    name: str,                    # 1-32 chars, lowercase, no spaces
    description: str,             # max 100 chars
    guild_ids: list[int] = None,  # instant deploy to specific guilds
)
async def cmd(ctx: discord.ApplicationContext, arg: str):
    await ctx.respond("Response")       # initial response (15s timeout)
    await ctx.send_followup("More")     # followup (no timeout)
```

### Interaction responses
```python
await interaction.response.send_message(content, ephemeral=True)  # only user sees
await interaction.response.defer()           # acknowledge, respond later
await interaction.followup.send(content)     # after defer
await interaction.response.edit_message(content)  # edit the message that triggered
```

### Voice
```python
vc = await voice_channel.connect()
vc.play(discord.FFmpegPCMAudio("audio.mp3"))  # play audio
vc.start_recording(sink, callback)             # record (py-cord extension)
await vc.disconnect()
```

## Pagination Patterns

Discord API uses cursor-based pagination with `before`, `after`, and `limit` parameters.

```python
# Fetch message history
async for message in channel.history(limit=100, before=some_message):
    process(message)

# Fetch members
async for member in guild.fetch_members(limit=1000):
    process(member)
```

REST API: `GET /channels/{id}/messages?before={snowflake}&limit=100`
Default limit: 50. Max limit: 100 per request.
Snowflake IDs encode timestamp — `before`/`after` are snowflake-based, not page numbers.

## Rate Limits

### Global
- **50 requests per second** per bot token (REST API global limit)
- **10,000 invalid requests per 10 minutes** triggers Cloudflare ban (returns 403 with HTML, not JSON)

### Per-route
Rate limits are per-route, identified by `X-RateLimit-Bucket` header.
Common route limits:
- **Send message**: 5 per 5s per channel
- **Edit message**: 5 per 5s per channel
- **Delete message**: 5 per 1s per channel (bulk delete: 1 per channel per rate limit window)
- **Add reaction**: 1 per 0.25s per channel
- **Webhook execute**: 5 per 2s per webhook
- **Guild member fetch**: 10 per 10s
- **Create DM**: 1 per 1s
- **Gateway IDENTIFY**: 1 per 5s (max 1000 per 24h per bot)

### Rate limit headers
```
X-RateLimit-Limit: 5           # requests allowed in window
X-RateLimit-Remaining: 3       # remaining in current window
X-RateLimit-Reset: 1470173023  # epoch seconds when window resets
X-RateLimit-Reset-After: 1.5   # seconds until reset (float)
X-RateLimit-Bucket: abc123     # unique bucket identifier
X-RateLimit-Scope: user        # user | global | shared
```

### 429 response
```json
{
  "message": "You are being rate limited.",
  "retry_after": 1.234,
  "global": false
}
```
If `global: true`, ALL routes are blocked. If `false`, only the specific route.
py-cord handles 429s automatically with built-in retry logic.

## Error Codes and Recovery

### HTTP status codes
| Code | Meaning | Recovery |
|------|---------|----------|
| 200 | Success | — |
| 201 | Created | — |
| 204 | No Content (success) | — |
| 304 | Not Modified | — |
| 400 | Bad Request | Check payload format, field lengths |
| 401 | Unauthorized | Invalid/expired token |
| 403 | Forbidden | Missing permissions or Cloudflare ban |
| 404 | Not Found | Invalid resource ID |
| 405 | Method Not Allowed | Wrong HTTP method |
| 429 | Rate Limited | Retry after `retry_after` seconds |
| 500 | Server Error | Retry with backoff |
| 502 | Gateway Unavailable | Retry with backoff |

### JSON error codes (common)
| Code | Description |
|------|-------------|
| 10003 | Unknown Channel |
| 10004 | Unknown Guild |
| 10008 | Unknown Message |
| 10013 | Unknown User |
| 30001 | Maximum guilds reached (100) |
| 30002 | Maximum friends reached (1000) |
| 30003 | Maximum pins reached (50) |
| 30005 | Maximum roles reached (250) |
| 30007 | Maximum webhooks reached (15 per channel) |
| 30010 | Maximum reactions reached (20) |
| 30013 | Maximum channels reached (500) |
| 30016 | Maximum invites reached (1000) |
| 40001 | Unauthorized (invalid token) |
| 40002 | Verification required |
| 50001 | Missing Access |
| 50008 | Cannot send messages in non-text channel |
| 50013 | Missing Permissions |
| 50014 | Invalid token provided |
| 50035 | Invalid Form Body |
| 50041 | Slowmode rate limited |

### Gateway close event codes
| Code | Description | Reconnectable |
|------|-------------|---------------|
| 4000 | Unknown error | Yes (resume) |
| 4001 | Unknown opcode | Yes (resume) |
| 4002 | Decode error | Yes (resume) |
| 4003 | Not authenticated | Yes (identify) |
| 4004 | Authentication failed | No — invalid token |
| 4005 | Already authenticated | Yes (resume) |
| 4007 | Invalid seq | Yes (identify) |
| 4008 | Rate limited | Yes (identify) |
| 4009 | Session timed out | Yes (identify) |
| 4010 | Invalid shard | No — fix shard config |
| 4011 | Sharding required | No — implement sharding |
| 4012 | Invalid API version | No — update library |
| 4013 | Invalid intent(s) | No — fix intent values |
| 4014 | Disallowed intent(s) | No — enable in portal |

### Voice close event codes
| Code | Description |
|------|-------------|
| 4001 | Unknown opcode |
| 4002 | Failed to decode payload |
| 4003 | Not authenticated |
| 4004 | Authentication failed |
| 4005 | Already authenticated |
| 4006 | Session no longer valid |
| 4009 | Session timeout |
| 4011 | Server not found |
| 4012 | Unknown protocol |
| 4014 | Disconnected (channel delete, voice moved, kicked) |
| 4015 | Voice server crashed |
| 4016 | Unknown encryption mode |

## SDK Idioms

### py-cord vs discord.py
py-cord is a fork. Key differences:
- Native `@bot.slash_command()` decorator (discord.py uses `discord.app_commands`)
- `discord.ui.Modal` built-in (discord.py added later)
- Voice recording with `Sink` classes (`WaveSink`, `MP3Sink`, custom sinks)
- `ApplicationContext` for slash commands vs `Interaction` in discord.py
- Import is still `import discord` — the package name is `py-cord` but module name is `discord`

### Event handler pattern
```python
@bot.event
async def on_ready():
    print(f"{bot.user} online")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return  # ALWAYS check — prevents infinite loops
    # process...
    await bot.process_commands(message)  # REQUIRED if using prefix commands
```

### Cog pattern (modular organization)
```python
class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command()
    async def hello(self, ctx):
        await ctx.respond("Hello")

bot.add_cog(MyCog(bot))
```

### Async executor pattern (blocking code in async context)
```python
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(None, blocking_function, args)
```
EOS uses this pattern extensively in `discord_bot.py` to call synchronous gateway
functions from async event handlers.

### Error handling
```python
@bot.event
async def on_application_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.respond("Missing permissions.", ephemeral=True)
    else:
        raise error
```

## Anti-Patterns

1. **Not checking `message.author.bot`** — causes infinite message loops when the bot
   responds to its own messages.
2. **Forgetting `await bot.process_commands(message)`** in `on_message` — silently
   breaks all prefix commands.
3. **Blocking the event loop** — synchronous HTTP calls, file I/O, or LLM calls in
   async handlers. Always use `run_in_executor()`.
4. **Hardcoding channel IDs** — use a config dict like `CHANNEL_IDS` or env vars.
5. **Not chunking messages** — sending > 2000 chars causes 400 errors silently caught
   by the library. User sees nothing.
6. **Using `WaveSink` for real-time voice** — records everything to one file. Use
   custom `SilenceDetectingSink` for utterance-level detection.
7. **Catching all exceptions silently** — voice WebSocket errors must be specifically
   filtered, not broadly silenced.
8. **Creating webhooks per-message** — webhooks are persistent. Create once, store URL.
9. **Using global intents when you only need guild** — `messages=True` enables both
   `guild_messages` and `dm_messages`. Use specific flags to minimize event volume.
10. **Not handling Gateway disconnects** — py-cord auto-reconnects by default, but
    custom voice logic needs manual reconnection handling.

## Data Model

### Snowflake IDs
All Discord IDs are snowflakes — 64-bit integers encoding creation timestamp.
Extract timestamp: `(snowflake >> 22) + 1420070400000` (ms since Discord epoch).
Always store as integers, not strings (Python handles big ints natively).

### Key objects
- **Guild** — a server. Contains channels, roles, members.
- **Channel** — text, voice, category, thread, forum, stage.
  Text channels: `TextChannel`. Voice: `VoiceChannel`. Threads: `Thread`.
- **Message** — content, author, embeds, attachments, reactions.
  Max 2000 chars content. Max 10 embeds. Max 10 files (25MB each, 100MB for boosted).
- **Member** — a user within a guild. Has roles, nick, permissions.
- **Role** — permission set assigned to members. Position-ordered (higher = more authority).
- **Webhook** — token-authenticated posting endpoint. Up to 15 per channel.

### Permission hierarchy
Server-level permissions → Channel-level overwrites → Role hierarchy.
`Administrator` permission bypasses all checks.
Bot role must be ABOVE managed roles in the role list to assign/remove them.

## Webhooks and Events

### Gateway events (WebSocket)
Connection flow: `HELLO` (heartbeat interval) -> `IDENTIFY` (token + intents) -> `READY`.
Reconnect: `RESUME` (session_id + last sequence number).

Key events used by EOS:
- `on_ready` — bot connected, cache populated
- `on_message` — new message in any accessible channel
- `on_voice_state_update` — member joins/leaves voice
- `on_member_join` / `on_member_remove` — guild membership changes
- `on_error` — unhandled exception in event handler

### Webhooks (HTTP)
```
POST https://discord.com/api/webhooks/{id}/{token}
Content-Type: application/json
{
  "content": "Hello",
  "username": "DEX",
  "avatar_url": "https://..."
}
```
Webhooks support: content, embeds, files, username/avatar override, thread targeting.
They do NOT trigger `on_message` for the bot itself (useful for avoiding loops).

## Limits

| Resource | Limit |
|----------|-------|
| Message content | 2,000 chars |
| Embed total | 6,000 chars |
| Embed title | 256 chars |
| Embed description | 4,096 chars |
| Embed fields | 25 per embed |
| Embed field name | 256 chars |
| Embed field value | 1,024 chars |
| Embed footer | 2,048 chars |
| Embeds per message | 10 |
| Files per message | 10 |
| File size | 25 MB (100 MB with boost level 2) |
| Channels per guild | 500 |
| Roles per guild | 250 |
| Webhooks per channel | 15 |
| Pins per channel | 50 |
| Reactions per message | 20 unique emoji |
| Guild members fetch | 1,000 per request |
| Bulk delete | 2-100 messages, < 14 days old |
| Slash command name | 1-32 chars (lowercase, no spaces, `a-z`, `0-9`, `-`, `_`) |
| Slash command description | 1-100 chars |
| Slash command options | 25 per command |
| Bot guilds | 100 (before verification), 2,500 (after) |

## Cost Model

Discord API is **free**. No per-request charges. No tiered pricing for API access.

Costs are indirect:
- **Compute** — hosting the bot process (EOS: Docker container on VPS)
- **Nitro / Server Boost** — increases file upload limits (8 -> 25 -> 100 MB)
- **Rate limit headroom** — higher traffic requires sharding and more compute

Webhooks are free and unlimited (within rate limits).
No cost difference between REST API calls and Gateway events.

## Version Pinning

- Discord API: **v10** (current stable, specified in base URL)
  - Base URL: `https://discord.com/api/v10/`
  - v9 deprecated. v6-v8 removed.
- py-cord: **2.7.1** (installed via `pip install py-cord`)
  - Requires Python 3.8+
  - Import as `import discord` (NOT `import pycord`)
  - pip package name: `py-cord` (conflicts with `discord.py` — only one can be installed)

Pin in requirements.txt: `py-cord==2.7.1`

---

# Tier 2 — Creator Intelligence

## Design Intent

Discord's API was designed for real-time communication bots in gaming communities, then
expanded to general-purpose automation. Key design tradeoffs:

1. **Gateway-first architecture** — events push to you via WebSocket rather than polling.
   This means the bot must maintain a persistent connection. If the connection drops,
   you miss events (no replay/catch-up unless you use audit logs or message history).

2. **Intent-based filtering** — after the intent system (API v8+), bots must declare
   which events they need. This was a privacy decision (preventing bots from passively
   collecting all member data) that became a performance feature (reducing event volume).

3. **Snowflake IDs as timestamps** — every ID encodes its creation time. This is
   intentional: it enables cursor-based pagination without secondary timestamp columns,
   and lets you extract "when was this created" from any ID without an API call.

4. **Rate limits as architecture** — Discord treats rate limits as a feature, not a bug.
   The bucket system lets them distribute capacity unevenly (send_message gets more
   headroom than create_channel) without a pricing tier. The 429 retry_after field
   is designed for automatic retry — the API expects bots to handle it.

5. **Webhooks as lightweight bots** — webhooks exist specifically for "post-only" use
   cases where maintaining a Gateway connection is overkill. They're Discord's answer
   to "I just want to send notifications." No auth, no intents, no events — just POST.

## Problem-Solution Map

### "Bot receives messages but content is empty"
Cause: `message_content` intent not enabled (code OR Developer Portal).
Fix: Enable in both places. This is the #1 new-bot debugging issue.

### "Bot connects then immediately disconnects"
Cause: Gateway close code 4014 — privileged intent requested but not enabled in portal.
Fix: Enable Message Content Intent, Server Members Intent, and/or Presence Intent
in the Developer Portal under Bot settings.

### "Messages from webhook don't appear"
Cause: Webhook URL invalid, channel deleted, or rate limited.
Fix: Check response status code. 404 = webhook deleted. 429 = rate limited.
Re-create webhook if 404.

### "Voice connection crashes the bot"
Cause: `_MissingSentinel` from `poll_voice_ws` — py-cord voice WebSocket exception
that bypasses on_error.
Fix: Set custom asyncio exception handler at event loop level (as EOS does).
Also guard voice connect behind `_bot_ready` flag.

### "Bot responds to itself infinitely"
Cause: Missing `if message.author.bot: return` check in `on_message`.
Fix: Always check. Also check `message.author == bot.user` if you have other bots.

### "Slash commands don't appear"
Cause: Global commands take up to 1 hour to propagate. Or bot lacks
`applications.commands` scope.
Fix: Use `guild_ids=[...]` for instant deployment during development.
Ensure OAuth invite URL includes `applications.commands` scope.

### "Embed exceeds maximum size"
Cause: Total embed characters > 6000, or individual field limits exceeded.
Fix: Validate embed size before sending. Use `chunk_message()` pattern for long content,
fall back to plain text if embed limits are hit.

### "Multiple scripts hitting 429 on webhook"
Cause: Webhook rate limit is 5 per 2s per webhook URL.
Fix: Add `time.sleep(0.5)` between posts (as EOS does). For high-throughput,
use multiple webhook URLs or queue posts.

## Operational Behavior

### Gateway heartbeat
After HELLO, Discord sends `heartbeat_interval` (typically 41,250ms).
Bot must send heartbeat every interval. Missing 2+ heartbeats = zombie connection.
py-cord handles this automatically. If you see "heartbeat blocked for more than X seconds,"
the event loop is blocked by synchronous code.

### Gateway resume vs identify
Resume: reconnect to same session, replay missed events.
Identify: new session, full cache rebuild, triggers `on_ready` again.
py-cord automatically resumes when possible. Forced identify happens on:
invalid sequence number, session timeout, or close codes 4007/4009.

### Message cache
py-cord caches the last 1000 messages by default (`max_messages` parameter).
`on_message_edit` and `on_message_delete` only fire for cached messages.
For uncached messages, use `on_raw_message_edit` / `on_raw_message_delete`.

### Connection lifecycle
Bot.run() blocks forever. It handles: connect, identify, heartbeat, reconnect.
For more control: `await bot.start(token)` in your own async loop.
`bot.close()` for graceful shutdown. Always call close in signal handlers.

### Thread safety
Discord objects are NOT thread-safe. All Discord API calls must happen on the
event loop thread. From synchronous code, use `asyncio.run_coroutine_threadsafe()`.
From async code in a different loop, use `bot.loop.call_soon_threadsafe()`.

## Ecosystem Position

### py-cord vs discord.py vs nextcord vs disnake
- **discord.py** (rapptz) — original library. Went on hiatus 2021, resumed 2022.
  Uses `discord.app_commands` for slash commands.
- **py-cord** (Pycord) — fork from discord.py 2.0 alpha. First-class slash commands,
  UI components, voice recording. Used by EOS.
- **nextcord** — another fork. Similar to py-cord, different maintainers.
- **disnake** — fork focused on API parity. Uses `disnake` import name (no conflict).

All four libraries use `import discord` EXCEPT disnake. py-cord and discord.py CANNOT
be installed simultaneously — they conflict on the `discord` package name.

### Complementary tools
- **Webhooks + requests** — lightweight posting without bot connection (EOS: `post_to_webhook`)
- **discord-interactions** — serverless slash command handling (Lambda/Cloud Functions)
- **Lavalink** — dedicated audio server for music bots (heavy voice use cases)

## Trajectory

### Recent changes (API v10, 2022-present)
- Message Content Intent became privileged (September 2022) — bots must opt-in
- Auto-moderation API added (configurable via bot)
- Forum channels added
- Voice messages support
- Application command permissions v2 (guild-level overrides)
- Select menus expanded (user, role, mentionable, channel selects)
- Onboarding API for new member flows

### Upcoming / in progress
- User-installable apps (bots that work in DMs without shared servers)
- Activities/Embedded apps (iframe-based interactive apps in voice channels)
- Monetization APIs (premium app subscriptions)
- Soundboard API
- Enhanced voice features

### Deprecation risks
- API v9 deprecated; v10 is current stable
- Gateway v8/v9 encoding changes may shift
- py-cord tracks discord.py loosely — breaking changes in discord.py may or may not
  propagate. Watch py-cord changelogs independently.

## Conceptual Model

```
User types in Discord channel
        |
        v
Discord Gateway (WebSocket)
        |
        v  (filtered by Intents)
py-cord event dispatcher
        |
        v
on_message(message)
        |
  +-----+-----+
  |             |
  v             v
Bot command?   EOS routing?
  |             |
  v             v
commands.Bot   intent_handler → EOSGateway
  handler        → cognitive_loop
                   → agent_runtime
                   → LLM
                   → response
                        |
                        v
                   channel.send() ← chunk_message()
                        |
                        v
                   Discord REST API → user sees response
```

Webhook flow (outbound only):
```
EOS script (cron/event)
        |
        v
post_to_webhook(content)
        |
        v
chunk_message() → list[str]
        |
        v  (for each chunk)
requests.post(webhook_url, json={content, username})
        |
        v  (rate limited: sleep 0.5s between chunks)
Discord displays message in channel
```

## Industry Expert

### Pattern: Channel-as-dashboard
EOS uses Discord channels as live dashboards — each channel is a specific domain
(pipeline, outreach, strategy). This is an expert pattern: instead of building
a separate dashboard UI, use Discord channels + webhook posts as a real-time
information radiator. The founder opens Discord and sees everything.

### Pattern: Hybrid bot + webhook architecture
The bot handles bidirectional conversation (inbound + outbound) while webhooks handle
fire-and-forget notifications from scripts. This dual-path architecture means:
- Scripts never need the bot's event loop
- Webhook posts don't trigger the bot's `on_message` (no loops)
- Bot stays focused on interactive conversation
- 15+ scripts can post independently without coupling

### Pattern: Utterance-level voice processing
Instead of recording entire voice sessions (WaveSink), EOS uses SilenceDetectingSink
to detect individual utterances with configurable silence threshold. This enables
real-time transcription and agent responses during live calls — turning Discord voice
into an AI-augmented meeting tool.

### Pattern: Intent-routed channel messages
Each channel has a routing hint in CHANNEL_MAP. Messages in `#lyfe-pipeline` automatically
route to the sales team agent. Messages in `#content-ideas` route to the content writer.
The channel IS the routing context — no slash commands needed, no explicit agent selection.

### Pattern: Multi-part message accumulation
When users split long messages across multiple sends (Part 1/3, Part 2/3, Part 3/3),
EOS detects the pattern and accumulates before processing. This handles a real Discord
UX limitation (2000 char limit) gracefully without requiring users to use slash commands
or file uploads.

### Pattern: Meeting mode
Voice input is contextually routed based on meeting type. Objection signals during
sales calls trigger the objection_handler sub-agent. Price questions get instant
scripted responses. The voice channel becomes a live sales copilot.

---

## EOS Usage Patterns

### Channel IDs (hardcoded in discord_bot.py)
13 channels with snowflake IDs: morning-brief, general, decisions, wins, agent-activity,
empyrean-strategy, empyrean-pipeline, empyrean-outreach, lyfe-strategy, lyfe-pipeline,
lyfe-outreach, brand-strategy, content-ideas.

### Message chunking standard
All EOS outbound messages use `chunk_message()` from `discord_utils.py`.
Limit: 1800 chars (200 char buffer). Split on paragraph boundaries.
Part labels: `*Part 1/N*` prepended to each chunk.

### Webhook posting standard
All scripts use `post_to_webhook()` from `discord_utils.py`.
Default webhook env var: `DISCORD_BRIEF_WEBHOOK`.
Default username: `DEX`. Sleep 0.5s between chunks.

### Voice standard
48kHz sample rate, stereo (2 channels), 16-bit samples.
Silence threshold: 1.5 seconds default.
STT: Groq Whisper large-v3-turbo.

## Gotchas

### Voice 4006 connection bug (UNRESOLVED)
Voice close code 4006 ("Session no longer valid") occurs intermittently.
py-cord does not auto-reconnect voice cleanly after 4006.
Current status: unresolved. Bot text functionality unaffected.

### _MissingSentinel crash (RESOLVED)
Voice WebSocket exceptions bypass `on_error`. Fixed with custom
`_handle_task_exception` handler on the asyncio event loop.

### Webhook 403 after Cloudflare ban
If any EOS script sends 10,000 invalid requests in 10 minutes
(e.g., malformed payloads in a loop), Cloudflare bans the IP for a period.
The response is HTML (not JSON). `post_to_webhook()` catches this as a generic exception.

### py-cord conflicts with discord.py
Both packages install as `import discord`. Installing one removes the other.
EOS uses py-cord. Never `pip install discord.py` on the EOS VPS.

### Channel ID changes on server recreation
If the Discord server is recreated, all hardcoded channel IDs in `CHANNEL_IDS` become
invalid. Bot will silently fail to find channels. Update all 13 IDs in discord_bot.py.
