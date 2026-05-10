# interfaces/

## Purpose
User-facing command/control surfaces — Discord, Telegram, CLI, voice, web.

## Status: STAGING
Interface-specific code currently lives in:
- `services/discord_bot.py` — primary Discord entrypoint
- `services/handlers/` — Discord command handlers
- `eos_ai/interfaces/` — dormant interface contracts
- `eos_ai/substrate/discord_*` — Discord transport modules

## Target Structure
```
interfaces/
├── discord/         # Discord-specific handlers, formatters
├── telegram/        # Telegram bot interface
├── cli/             # Command-line tools
├── voice/           # Voice input/output
└── web/             # Web UI (future)
```

## Rules
- Interfaces call substrate — they never implement their own reasoning
- Surface-specific formatting belongs here, not in substrate
- Command parsing and validation belongs here

> Created: Phase 96.8BK — 2026-05-09
