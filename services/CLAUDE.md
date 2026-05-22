# services — Legacy Entrypoints (being migrated)

## Identity
Legacy daemon processes. Post-unification, primary interfaces
live in `transports/` — intelligence lives in `substrate/`.
This directory retained for compatibility during migration.

## Services
discord_bot.py         — DEX Discord bot (legacy, still in os-discord container)
operator_api.py        — Operator REST API (legacy)
higgsfield_webhook.py  — media generation webhook

## Post-unification equivalents
transports/discord/bot.py            — substrate-wired Discord bot
transports/discord/signal_factory.py — message → SignalEnvelope
transports/api/operator.py           — substrate-wired operator API

## Discord bot
- Library: py-cord 2.6.1
- AI name: from get_ai_name() not hardcoded
- FOUNDER_DISCORD_ID triggers auto-join voice
- Voice: SilenceDetectingSink + Groq STT
- Voice status: 4006 connection bug unresolved
- Text: routed through substrate.execute() (general path)

## Env files
services/.env — bot tokens + Discord IDs
eos_ai/.env   — Anthropic + Neon keys

## Never do
- Never hardcode AI name
- Never use WaveSink for voice recording
- Never use fixed-time recording chunks
