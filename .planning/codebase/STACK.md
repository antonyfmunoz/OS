# Technology Stack

*Generated: 2026-03-26*
*Focus: tech*

## Summary

EntrepreneurOS is a dual-layer system: a Python 3.12 AI intelligence layer (`eos_ai/`) running inside Docker on a VPS, and a TypeScript/Hono SaaS API layer (`eos_saas/`) backed by Neon PostgreSQL. The primary runtime surface is Telegram + Discord bots. A web frontend is planned but not yet built.

---

## Languages

**Primary:**
- Python 3.12 — all AI agents, automation scripts, bots, scraping, webhooks (`eos_ai/`, `13_Scripts/`)
- TypeScript 5.4 — SaaS API layer, database schema, migrations (`eos_saas/`)

**Secondary:**
- Bash/Shell — deployment scripts, Docker management (historical; most migrated to Python)

---

## Runtime

**Python Environment:**
- Python 3.12.3 (VPS system Python; Docker image uses `python:3.11-slim`)
- `dotenv` pattern: two separate `.env` files — `13_Scripts/.env` (bot tokens) and `eos_ai/.env` (AI keys + DB)

**Node.js:**
- Node.js 20.20.1
- Package manager: npm (lockfile: `eos_saas/package-lock.json`)

---

## Docker Services

All services defined in `/opt/OS/docker-compose.yml`. All mount `/opt/OS` as `/app`.

| Service | Command | Notes |
|---|---|---|
| `os-bot` | `python3 13_Scripts/telegram_control.py` | restart: always |
| `os-monitor` | `python3 13_Scripts/dm_monitor.py` | network_mode: host, shm 2GB |
| `os-scraper` | `python3 13_Scripts/overnight_scrape.py` | restart: no (on-demand) |
| `os-webhook` | `python3 13_Scripts/calendly_webhook.py` | port 8080:8080 |
| `os-discord` | `python3 13_Scripts/discord_bot.py` | network_mode: host |

Dockerfile base: `python:3.11-slim`. System packages: `git curl gcc python3-dev ffmpeg espeak`. Playwright Chromium installed at build time. PyTorch CPU build installed separately before `requirements.txt`.

---

## Python Dependencies (`13_Scripts/requirements.txt`)

**Critical:**
- `anthropic` — Claude Haiku + Sonnet via Anthropic API (primary LLM)
- `google-genai` — Gemini 2.0 Flash (vision, documents, embeddings)
- `psycopg2-binary` — Neon PostgreSQL connection
- `playwright` — browser automation, DM monitor, browser agent
- `python-telegram-bot` — Telegram bot interface
- `py-cord[voice]==2.6.1` — Discord bot with voice support (patched at build time via `patch_pycord.py`)
- `flask` — Calendly webhook receiver
- `faster-whisper` — local speech-to-text (primary)
- `openai-whisper` — Whisper fallback (installed in Dockerfile, not requirements.txt)
- `yt-dlp` — audio extraction from video URLs
- `silero-vad` — neural voice activity detection
- `webrtcvad` — VAD fallback
- `librosa` / `numpy` — audio processing

**Installed separately in Dockerfile:**
- `torch` (CPU) — required by silero-vad and audio processing
- `openai-whisper`
- `yt-dlp`

**Not in requirements.txt but used in eos_ai:**
- `fastembed` — BAAI/bge-small-en-v1.5 embedder (384-dim, ONNX, no GPU) — must be installed separately with `--break-system-packages`

---

## TypeScript/SaaS Dependencies (`eos_saas/package.json`)

**Framework:**
- `hono` 4.12.8 + `@hono/node-server` 1.19.11 — HTTP API framework (replaces Express)
- `tsx` 4.19.2 — TypeScript runner (no compile step required for dev/prod)

**Database:**
- `drizzle-orm` 0.39.3 — type-safe ORM
- `drizzle-kit` 0.30.4 — migrations and schema push
- `@neondatabase/serverless` 0.10.4 — Neon PostgreSQL serverless driver

**Validation:**
- `zod` 3.23.8 — schema validation

**Other:**
- `ws` 8.20.0 — WebSocket support

---

## AI Models in Use

| Model | ID | Use |
|---|---|---|
| Claude Haiku | `claude-haiku-4-5-20251001` | scoring, classification, summaries |
| Claude Sonnet | `claude-sonnet-4-6` | generation, analysis, deep reasoning |
| Gemini 2.0 Flash | `gemini-2.0-flash` | image/video/document processing, vision fallback |
| Google Text Embedding 004 | `text-embedding-004` | 768-dim embeddings (when Gemini key present) |
| BAAI/bge-small-en-v1.5 | local via fastembed | 384-dim semantic search (local, no GPU) |
| faster-whisper | local | speech-to-text (primary) |
| Qwen2.5:3b | local via Ollama | free/fast Discord voice routing, simple queries |
| Coqui TTS | local | text-to-speech for Discord voice |
| espeak | system package | TTS fallback |

---

## Database

**Primary:** Neon (serverless PostgreSQL)
- Python access: `psycopg2` via `eos_ai/db.py` — RLS enforced with `SET LOCAL app.current_org_id`
- TypeScript access: `@neondatabase/serverless` + `drizzle-orm` via `eos_saas/db/`
- Schema defined in: `eos_saas/db/schema.ts`
- Migrations: `eos_saas/db/migrations/`
- pgvector extension used for 768-dim embedding storage

**Key tables:** `interactions`, `embeddings`, `outcomes`, `human_profiles`, `agents`, `skills`, `tasks`, `entity_links`, `events`, `ventures`, `organizations`, `approvals`, `user_intelligence_profiles`, `cross_product_permissions`

---

## Build and Dev Tools

- `drizzle-kit` — schema generation, migration push, Drizzle Studio
- `tsx` — runs TypeScript directly (no tsc compile step)
- Docker Compose — all services, always-on deployment
- Playwright — installed at Docker build time with Chromium

---

## Configuration

**Environment files:**
- `13_Scripts/.env` — `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `APIFY_API_TOKEN`, `DISCORD_BOT_TOKEN`, `FOUNDER_DISCORD_ID`, channel IDs, `CALENDLY_SIGNING_KEY`
- `eos_ai/.env` — `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `DATABASE_URL`, `EOS_ORG_ID`, `EOS_USER_ID`, `AI_NAME`
- `.env.example` — root-level example (committed, no secrets)

**Timezone:** All containers set `TZ=America/Los_Angeles`

---

## Platform

**Current deployment:** Single VPS at `100.77.233.50`, Tailscale private network
**Production target:** Single VPS (founder-only validation phase); cloud infra planned pre-public-launch
**Frontend status:** Not yet built — Phase 2 target is Stitch (Google Gemini-backed design-to-code)

---

## Key Files

- `/opt/OS/docker-compose.yml` — all service definitions
- `/opt/OS/Dockerfile` — Python 3.11-slim base, all system deps, Playwright
- `/opt/OS/13_Scripts/requirements.txt` — all Python deps
- `/opt/OS/eos_saas/package.json` — TypeScript/Node deps
- `/opt/OS/eos_ai/agent_runtime.py` — model routing (Haiku vs Sonnet), cost table
- `/opt/OS/eos_ai/embedder.py` — fastembed singleton, BAAI/bge-small-en-v1.5
- `/opt/OS/eos_ai/db.py` — Neon connection + RLS pattern
- `/opt/OS/eos_saas/db/schema.ts` — full Drizzle schema with pgvector
- `/opt/OS/patch_pycord.py` — py-cord voice bug patch (applied at Docker build)
