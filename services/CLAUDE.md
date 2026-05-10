# services — Live Entrypoints

## Identity
Live daemon processes that serve as UMH's interface surfaces.
These are entrypoints, not intelligence — intelligence lives
in `eos_ai/` (the runtime layer).

## Services
discord_bot.py       — DEX Discord bot (primary UMH interface)
telegram_control.py  — Telegram bot (dormant)
dm_monitor.py        — Instagram DM monitor
calendly_webhook.py  — booking webhook receiver
higgsfield_webhook.py — media generation webhook

## Discord bot
- Library: py-cord 2.6.1
- AI name: from get_ai_name() not hardcoded
- FOUNDER_DISCORD_ID triggers auto-join voice
- Voice: SilenceDetectingSink + Groq STT
- Voice status: 4006 connection bug unresolved
- Text: working

## Env files
services/.env — bot tokens + Discord IDs
eos_ai/.env   — Anthropic + Neon keys

## Never do
- Never hardcode AI name
- Never use WaveSink for voice recording
- Never use fixed-time recording chunks
