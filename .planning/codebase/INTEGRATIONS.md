# External Integrations

*Generated: 2026-03-26*
*Focus: tech*

## Summary

EOS integrates across messaging platforms (Telegram, Discord), Google Workspace, scraping infrastructure (Apify, Playwright), AI APIs (Anthropic, Google Gemini, OpenAI), and sales tooling (Calendly). All secrets are in `services/.env` and `eos_ai/.env`. Auth is currently founder-only — Firebase and Stripe are planned but not implemented.

---

## AI APIs

**Anthropic (primary LLM)**
- SDK: `anthropic` Python package
- Auth env var: `ANTHROPIC_API_KEY` (in `eos_ai/.env` and passed to all containers)
- Models: `claude-haiku-4-5-20251001` (fast/cheap), `claude-sonnet-4-6` (primary generation)
- Routing module: `eos_ai/agent_runtime.py`
- Cost tracking: tracked per-call, stored in `interactions` table and `services/cost_log.json`

**Google Gemini**
- SDK: `google-genai` Python package (`google.genai` new SDK, falls back to `google.generativeai`)
- Auth env var: `GEMINI_API_KEY`
- Models: `gemini-2.0-flash` (vision, documents, image, video analysis), `text-embedding-004` (768-dim embeddings)
- Used in: `eos_ai/media_processor.py`, `eos_ai/embedding_engine.py`

**OpenAI**
- SDK: available in stack
- Status: present but not default routing path — referenced as fallback in Whisper (`openai-whisper` package)

**Ollama (local)**
- Model: `qwen2.5:3b`
- Purpose: free/fast routing for Discord voice simple queries, reduces Anthropic spend
- Used in: `eos_ai/voice_engine.py` (Discord-specific)

---

## Messaging Interfaces

**Telegram Bot API**
- Library: `python-telegram-bot`
- Auth env vars: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- Service: `os-bot` → `services/telegram_control.py`
- Purpose: primary founder control interface — 40+ commands, NLP routing, voice messages, media, morning brief, approval queue
- AI name resolved from BIS at runtime via `get_ai_name()` — never hardcoded

**Discord Bot**
- Library: `py-cord[voice]==2.6.1` (patched at Docker build via `patch_pycord.py`)
- Auth env vars: `DISCORD_BOT_TOKEN`, `FOUNDER_DISCORD_ID`, channel IDs (multiple)
- Service: `os-discord` → `services/discord_bot.py`
- Purpose: DEX conversational bot, auto-joins founder voice channel, routes text through EOS gateway
- Voice pipeline: SilenceDetectingSink → Groq STT → speech classification → Ollama (simple) or Claude (complex) → Coqui TTS
- Known issue: 4006 connection bug in voice unresolved (patched at build time to prevent crash)

---

## Google Workspace

**GWS CLI connector**
- Implementation: `eos_ai/gws_connector.py` — subprocess calls to `gws` CLI
- Products integrated: Google Calendar, Gmail, Google Drive, Google Tasks
- Auth: OAuth via `gws` CLI (keyring-based), credentials on VPS filesystem
- Status: operational on VPS

**Calendar**
- Methods: `get_today_events()`, `get_week_events()` — used in morning brief and meeting context
- Used in: `eos_ai/orchestrator.py` (6am cron), `eos_ai/voice_interface.py`

**Gmail**
- Methods: inbox scanning, contact extraction — used for relationship tracking and onboarding backfill
- Used in: `eos_ai/onboarding_backfill.py`

**Google Drive**
- Methods: document access for knowledge base ingestion
- Used in: `eos_ai/onboarding_backfill.py`, `eos_ai/gws_scanner.py`

**Google Tasks**
- Methods: task sync and delegation
- Used in: `eos_ai/gws_connector.py`

**Partial (MCP — not on VPS):**
- Gmail MCP, Google Calendar MCP — connected on claude.ai, not wired to VPS runtime

---

## Scraping & Data Collection

**Apify**
- Auth env var: `APIFY_API_TOKEN`
- Purpose: Instagram comment scraping for ICP signal harvesting
- Used in: `services/apify_scraper.py`
- Target accounts: competitor Instagram accounts (`hormozi`, `imangadzhi`, etc.)
- Output: `01_Inbox/raw_signals/` directory (JSON files)

**Playwright (browser automation)**
- Installed: Chromium at Docker build time
- Purpose: Instagram DM inbox monitoring, browser agent (built, not yet wired to agents)
- Service: `os-monitor` → `services/dm_monitor.py`
- Advanced use: `eos_ai/browser_agent.py` — full web operator for agent execution layer (built, not wired)

---

## Sales & CRM Tooling

**Calendly**
- Auth env var: `CALENDLY_SIGNING_KEY` (HMAC signature verification)
- Service: `os-webhook` → `services/calendly_webhook.py` (Flask, port 8080)
- Inbound webhook: `invitee.created` and `invitee.canceled` events → trigger sales call brief → Telegram alert
- RLHF integration: Calendly bookings logged to `interactions` table as outcome signals

**Typeform**
- Purpose: lead qualification forms (referenced in architecture)
- Status: configured externally, not directly integrated in codebase

**ManyChat**
- Purpose: Instagram DM automation layer
- Status: external configuration, not directly in codebase

---

## Database

**Neon (serverless PostgreSQL)**
- Auth env var: `DATABASE_URL` (in `eos_ai/.env`)
- Python client: `psycopg2-binary` via `eos_ai/db.py`
- TypeScript client: `@neondatabase/serverless` + `drizzle-orm` via `saas/db/`
- RLS: row-level security enforced via `SET LOCAL app.current_org_id`
- Extensions: pgvector (768-dim embeddings)

---

## Voice & Audio

**faster-whisper (local STT)**
- No external auth required — runs locally
- Purpose: primary speech-to-text for Telegram voice messages and Discord
- Used in: `eos_ai/media_processor.py`, `eos_ai/voice_engine.py`

**Coqui TTS (local TTS)**
- No external auth — runs locally
- Purpose: Discord voice responses
- Fallback: `espeak` (system package in Dockerfile)

**Silero VAD + webrtcvad (local)**
- Purpose: voice activity detection in Discord voice pipeline
- No external auth required

---

## Webhooks

**Incoming:**
- `POST /` (port 8080) — Calendly booking events, HMAC-verified with `CALENDLY_SIGNING_KEY`
  - Service: `os-webhook` → `services/calendly_webhook.py`

**Outgoing:**
- Telegram Bot API — alerts, morning briefs, approval notifications from all services

---

## Planned / Not Yet Implemented

| Integration | Purpose | Blocker |
|---|---|---|
| Firebase Auth | Public user sign-up, Google/Apple OAuth | Phase 2 — not started |
| Stripe | Subscription billing, usage-based AI cost | Phase 2 — not started |
| Notion OAuth | VPS-side OAuth for interim dashboard | MCP only, needs VPS auth |
| Slack (deep) | Team coordination | Future |
| HubSpot / Salesforce | CRM at scale | Future |
| QuickBooks | Finance integration | Future |
| GitHub | Dev workflow integration | Future |
| LinkedIn | Outreach automation | Future |
| WhatsApp Business | Messaging channel | Future |

---

## Environment Variable Reference

| Var | File | Used By |
|---|---|---|
| `ANTHROPIC_API_KEY` | `eos_ai/.env` | all containers (passed via docker-compose env) |
| `GEMINI_API_KEY` | `eos_ai/.env` | `media_processor.py`, `embedding_engine.py` |
| `DATABASE_URL` | `eos_ai/.env` | `db.py`, `saas/` |
| `EOS_ORG_ID` | `eos_ai/.env` | `db.py`, all agent context |
| `EOS_USER_ID` | `eos_ai/.env` | `db.py`, all agent context |
| `AI_NAME` | `eos_ai/.env` | `business_instance.py` (fallback if BIS unavailable) |
| `TELEGRAM_BOT_TOKEN` | `services/.env` | `telegram_control.py`, `calendly_webhook.py` |
| `TELEGRAM_CHAT_ID` | `services/.env` | `telegram_control.py`, all alert senders |
| `DISCORD_BOT_TOKEN` | `services/.env` | `discord_bot.py` |
| `FOUNDER_DISCORD_ID` | `services/.env` | `discord_bot.py` (auto-join voice trigger) |
| `APIFY_API_TOKEN` | `services/.env` | `apify_scraper.py` |
| `CALENDLY_SIGNING_KEY` | `services/.env` | `calendly_webhook.py` |

---

## Key Files

- `/opt/OS/eos_ai/agent_runtime.py` — Anthropic SDK calls, model routing, cost calculation
- `/opt/OS/eos_ai/media_processor.py` — Gemini integration for vision/docs/audio
- `/opt/OS/eos_ai/gws_connector.py` — Google Workspace via gws CLI subprocess
- `/opt/OS/eos_ai/gws_scanner.py` — GWS document ingestion
- `/opt/OS/eos_ai/voice_engine.py` — Discord voice pipeline (Silero → Whisper → Ollama/Claude → Coqui)
- `/opt/OS/eos_ai/browser_agent.py` — Playwright web operator (built, not wired to agents)
- `/opt/OS/services/telegram_control.py` — Telegram bot, primary founder interface
- `/opt/OS/services/discord_bot.py` — Discord bot, voice + text
- `/opt/OS/services/dm_monitor.py` — Playwright Instagram DM monitor
- `/opt/OS/services/apify_scraper.py` — Apify Instagram comment scraper
- `/opt/OS/services/calendly_webhook.py` — Flask Calendly webhook receiver
- `/opt/OS/eos_ai/db.py` — Neon connection, RLS, venture/skill ID resolution
- `/opt/OS/saas/db/schema.ts` — full Drizzle schema, pgvector, all enums
