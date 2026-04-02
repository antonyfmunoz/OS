# services — Bots and services

## Services
discord_bot.py       — DEX Discord bot
telegram_control.py  — Telegram bot
dm_monitor.py        — Instagram DM monitor

## Discord bot
- Library: py-cord 2.6.1
- AI name: from get_ai_name() not hardcoded
- FOUNDER_DISCORD_ID triggers auto-join voice
- Voice: SilenceDetectingSink + Groq STT
- Voice status: 4006 connection bug unresolved
- Text: working

## Env files
services/.env — bot tokens + Discord IDs
eos_ai/.env     — Anthropic + Neon keys

## Never do
- Never hardcode AI name
- Never use WaveSink for voice recording
- Never use fixed-time recording chunks
