---
type: codewiki-dir
dir: config
---

# `config/` — committed non-secret environment configuration

**1 file · 7,862 bytes · [Full file inventory](../inventory/config.md)**

## Purpose
`config/` holds a single file, `config/nonsecret.env` (136 lines) — the *safe-to-commit*
half of UMH's environment. It is the deliberate counterpart to the 1Password vault: every
value here is a non-secret identifier (public Discord snowflake channel IDs, Notion page/DB
UUIDs, EOS org/user/portfolio IDs, the AI name `DEX`, the public domain, Ollama base URL,
Discord-router channel routing). The file's own header states the rule: "safe to commit."
Secrets never appear here — they resolve at runtime through 1Password.

## How it fits
This is configuration data, not code — it sits outside the projections → transports →
adapters → substrate layer stack. It is loaded into a shell session with
`set -a; source config/nonsecret.env; set +a`, exposing its keys as environment variables
that substrate/transport code then reads at runtime (the Instance Context Law requires
substrate code to read identity like `AI_NAME` and org IDs from env/BIS, never hardcode
them). It is the plaintext, git-tracked layer; `infra/docker/umh.env` and `services/.env.tpl`
are the 1Password-injected secret layers.

## Structure
A flat `.env` file organized by commented section: Identity (`AI_NAME=DEX`, `TZ`),
Infrastructure (`OLLAMA_BASE_URL`, `UMH_PUBLIC_DOMAIN=universalmetaharness.tech`), EOS
Identity (org/user/portfolio UUIDs), Discord channel IDs (8 channels incl.
`DISCORD_FOUNDERS_OFFICE`), Instagram username, EOS Discord router config (builder/product
session routing), Local Bridge (Beast IP/port), UMH Router (`claude_cli` session targets),
Notion signal sources, NotebookLM IDs, and a long block of Notion page/DB IDs across four
ventures (Personal Brand, Lyfe Institute, Empyrean Creative, Portfolio Overview).

## Data & state
Read-only config source. Consumers `source` it into their environment. The values are
*instance* data for this specific UMH tenant (AFM's deployment) — a different tenant would
supply different IDs. Note the memory-referenced single-domain rule holds:
`UMH_PUBLIC_DOMAIN=universalmetaharness.tech` (never `umh-cockpit.fly.dev`).

## Gotchas
- **`INSTAGRAM_USERNAME=afm_bot` is here; the password is NOT** — the comment explicitly
  routes the password to 1Password. This is the pattern for every credentialed service:
  the public handle is committable, the secret is vaulted.
- Discord IDs here are **public snowflake IDs**, not secrets — but `DISCORD_FOUNDERS_OFFICE`
  (1485765456739696714) is load-bearing and must never be recreated (per the Founders Office
  memory). `FOUNDER_DISCORD_ID` gates who the Discord text transport accepts.
- These values are **instance context** (this tenant's identity). Substrate code must read
  them at runtime via env/`get_ai_name()`/BIS, never inline them — the Instance Context Law
  pre-commit hook (`scripts/check_instance_leak.py`) enforces this on `substrate/`.
- `UMH_DEV_BYPASS=true` is set here — a dev convenience flag; be aware it is committed.

## See also
- [`infra/`](infra.md) — the secret half: `infra/docker/umh.env` (1Password `op://` refs)
- [`_root-files`](_root-files.md) — `.env.example`, `.env.sessions.tpl`, `docker-compose.yml`
- [conventions](../conventions.md) — Instance Context Law, secret handling
- [architecture](../architecture.md)
