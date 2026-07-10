---
type: codewiki-dir
dir: _root-files
---

# Repository root files — the constitution, the build/deploy surface, and the campaign archive

**35 files · 250,428 bytes · [Full file inventory](../inventory/_root-files.md)**

## Purpose
The repository root holds the documents and files that govern the entire system rather than
any one directory: the **constitution docs** every AI session must load (CLAUDE.md,
ARCHITECTURE.md, PLATFORM_SPEC.md, PHILOSOPHY.md, EPISTEMOLOGY.md, PROTOCOLS.md), the
**build/deploy surface** (`docker-compose.yml`, `Dockerfile`, `pyproject.toml`,
`requirements.txt`, `Makefile`, `install.sh`, `setup.sh`, `patch_pycord.py`), the **campaign
report archive** (C31–C33, historical), and configuration/lock files (`.env` templates,
`.mcp.json`, `skills-lock.json`, `.gitignore`, `.dockerignore`).

## How it fits
These files sit above the four-layer code stack (projections → transports → adapters →
substrate) and define its rules. `CLAUDE.md` and `.claude/rules/*.md` encode the laws the
pre-commit hooks enforce (type coherence, projection boundary, architecture layers, instance
context, CPU gate). `ARCHITECTURE.md` and `PLATFORM_SPEC.md` are the master spec — the latter
is **FROZEN at v1.0.0** and changes only through the Breaking Change Process. `docker-compose.yml`
is the deployment entrypoint that wires the whole `services/` layer into running containers.

## Structure — the four groups

**Constitution / spec (load-order docs):**
| File | Lines | Role |
|---|---|---|
| `README.md` | 115 | Public overview: what UMH is, quick install, 8 injection layers, stage system |
| `cloud.md` | 78 | System context loaded first in every session; the retrieval hierarchy (palace → graph → summaries → raw → logs) |
| `CLAUDE.md` | 478 | The Developer Agent soul document + all enforced laws (CPU gate, type coherence, completion standards) |
| `CLAUDE.local.md` | 53 | Gitignored local preferences (communication style, completion standards) |
| `AGENTS.md` | 23 | Cross-agent config read by all AI coding tools |
| `ARCHITECTURE.md` | 565 | Architecture & master specification |
| `PLATFORM_SPEC.md` | 906 | Platform Specification v1.0.0 — **FROZEN** (est. 2026-06-30, frozen 2026-07-01 after C40B production certification) |
| `PHILOSOPHY.md` | 489 | Why the system exists; Reality/Intelligence/Personalization/Execution |
| `EPISTEMOLOGY.md` | 952 | How the organism learns; templates as f(invariants, parameters, context) |
| `PROTOCOLS.md` | 282 | The 4 protocol layers (L0 AI identity → L3) |

**Build / deploy:**
| File | Lines | Role |
|---|---|---|
| `docker-compose.yml` | 224 | Application service orchestration — 6 services (see below) |
| `Dockerfile` | 18 | `python:3.11-slim` image; installs deps, Playwright chromium, claude-code CLI, runs `patch_pycord.py` |
| `pyproject.toml` | 60 | Package metadata, optional-dependency extras (voice/perception/telegram/scraping/agents), ruff + pytest config (`target-version py311`) |
| `requirements.txt` | 25 | Runtime pip deps (py-cord[voice]==2.6.1, anthropic, google-genai, faster-whisper, groq, notion-client, …) |
| `Makefile` | 7 | Two targets — `test-migration` and `test-migration-offline` |
| `install.sh` | 69 | One-line installer: prereq checks, clone/pull, env file scaffold |
| `setup.sh` | 65 | First-run wizard: installs deps + Ollama, runs `runtime.setup_wizard` |
| `patch_pycord.py` | 121 | **Build-time patch of py-cord's `voice_client.py`** — guards three `_MissingSentinel` crash sites that cause the Discord 4006 voice session-invalidation loop |

**Campaign archive (historical, retired):** `C31_CAMPAIGN_REPORT.md`,
`C31_GROUND_TRUTH_AUDIT.md`, `C31_PHASE2A/2B/2C_REPORT.md`, `C31_PHASE3–6_REPORT.md`,
`C32_CAMPAIGN_REPORT.md`, `C33_CAMPAIGN_REPORT.md` — 14 files documenting the substrate
convergence campaigns (C31–C33). Campaign engineering (C34–C40B) is **retired**; these are
kept as history, not active spec.

**Config / lock:** `.env.example`, `.env.sessions.tpl` (Claude Code OAuth via 1Password),
`.dockerignore`, `.gitignore` (163 lines), `.mcp.json` (registers the `context7` MCP server),
`skills-lock.json` (pins 4 GitHub-sourced skills: humanizer, improve, karpathy-guidelines,
last30days).

## The application services (`docker-compose.yml`)
Six services on the `eos_network` bridge, each with a hard CPU/memory cap (CPU Gate Law):

| Service | Container | Command | CPU cap | Restart | Role |
|---|---|---|---|---|---|
| `os-discord` | `os-discord` | `services/discord_bot.py` | 0.35 / 1G | on-failure | Primary conversational interface; mounts host tmux socket to reach the `dex_main` CC session |
| `os-operator` | `os-operator` | `uvicorn services.operator_api:app :8091` | 1.00 / 2G | unless-stopped | Operator workstation API + cockpit backend; has healthcheck; mounts docker.sock + mesh SSH key |
| `os-webhook` | `os-webhook` | `transports/api/webhooks/calendly_webhook.py` | 0.25 / 128M | always | Inbound webhook receiver (:8080) |
| `os-browser` | `os-browser` | `services/browser_relay.py` | 0.50 / 1280M | unless-stopped | Playwright browser relay (:8086), 512m shm |
| `os-livekit` | `os-livekit` | `livekit-server` v1.8.3 | 0.35 / 256M | unless-stopped | WebRTC voice server; config from `infra/livekit.yaml` |
| `os-scraper` | `os-scraper` | `services/overnight_scrape.py` | 0.25 / 256M | **no** | One-shot nightly scraper — run via cron `docker-compose run`, not always-on |

The README lists three headline services (os-discord/os-webhook/os-operator); the compose
file defines six. `os-scraper` is a scheduled job, not a persistent service — it is
correctly absent from `docker ps`.

## Data & state
The compose services bind-mount `${UMH_ROOT:-/opt/OS}` into `/app` — **the live checkout is
the containers' source**, so editing files under `/opt/OS` changes running services (do not
branch/commit there; use a worktree). Secrets load via `env_file: infra/docker/umh.env`
(1Password-resolved) + `services/.env`. `patch_pycord.py` mutates
`site-packages/discord/voice_client.py` inside the image at build time.

## Gotchas
- **`PLATFORM_SPEC.md` is FROZEN** — any contract change needs the 5-step Breaking Change
  Process (RFC + migration + regression qualification + version bump + owner approval). Do
  not edit it casually.
- **`docker-compose.yml` bind-mounts the live checkout** into every service. The main
  `/opt/OS` checkout is the runtime's file source — executors must READ it but branch/write
  ONLY in an isolated worktree (a wave-1 executor once branch-switched `/opt/OS` mid-run and
  broke the trunk).
- **Docker images run Python 3.11** (`FROM python:3.11-slim`). Never use 3.12+ syntax
  (backslash-in-f-string-expression, etc.) in code that runs in a container.
- **`patch_pycord.py` must survive py-cord upgrades.** It uses regex to capture actual
  indentation across python 3.11/3.12/3.13 site-packages paths; if the 4006 voice loop
  returns, verify all three patch sites still applied (it prints per-site status).
- Never rebuild Docker for a Python-only change — the checkout is bind-mounted, so a
  `docker restart` picks up code edits. Rebuild only when `Dockerfile`/`requirements.txt`
  change.
- The C31–C33 reports are **historical**. Campaign engineering is retired; treat them as an
  audit trail, not current roadmap (the roadmap is P1–P3 in CLAUDE.md).

## See also
- [architecture](../architecture.md) · [tech-stack](../tech-stack.md) · [conventions](../conventions.md)
- [services-runtime](../services-runtime.md) — what these compose services look like running
- [`services/`](services.md) — the entrypoint modules the compose commands invoke
- [`infra/`](infra.md) · [`docker/`](docker.md) · [`config/`](config.md) · [`.github/`](dot-github.md)
- [`.claude/`](dot-claude.md) — the rules the root laws reference
