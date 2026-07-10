---
type: codewiki-dir
dir: services
---

# `services/` — deployment entrypoints (process `main()`s, no business logic)

**43 files · 726,549 bytes · [Full file inventory](../inventory/services.md)**

## Purpose
`services/` holds the process entry points — the scripts that a Docker container,
systemd unit, or cron job actually launches. By the architecture-layer law a service is
supposed to be *only* a deployment entrypoint: wire up sockets, start a loop or server,
and delegate; business logic lives in `substrate/`, `adapters/`, and `transports/`.
`services/CLAUDE.md` labels the directory "Legacy Entrypoints (being migrated)," which
is accurate: the newest surfaces (the operator API, webhooks) have moved to
`transports/`, while the Discord bot, trackers, bridges, and scrapers still run from
here. Several files here are genuinely large (`discord_bot_commands.py` at 3,113 lines,
`discord_bot.py` at 1,915) and hold real handler logic — that is the migration debt this
directory's own note flags.

## How it fits
`services/` is the top of the runtime stack: it is launched, it is never imported by
`substrate/`, `adapters/`, or `transports/` (those layers must never import upward into
services). A service's job at startup is to call `adapters/socket_registration.py`'s
`register_all_sockets()` so substrate ports can reach concrete adapters, then start its
loop. The full picture of which process runs where, health, and restart semantics lives
in [services-runtime.md](../services-runtime.md) — this page covers the directory's
contents and the container mapping only.

## Structure
The directory is essentially flat — one package subdir plus 40 root files.

| Group | Files | Role |
|---|---|---|
| Discord bot | `discord_bot.py` (1,915), `discord_bot_commands.py` (3,113), `discord_message_handlers.py` (1,367) | The DEX conversational layer — the `os-discord` container entry point and its extracted command/message handlers. |
| Operator API | `operator_api.py` (809) | FastAPI backend for the operator UI — the `os-operator` container entry point (`uvicorn services.operator_api:app`). |
| Bridges | `local_bridge_server.py`, `local_bridge_client.py`, `bridge_health.py`, `export_bridge_handler.py`, `cc_webhook_receiver.py` | The Windows/WSL local bridge and its VPS-side watchdog; the CC Stop-hook reply receiver. |
| Browser / relay | `browser_relay.py` (583), `browser_adapter.py` | The `os-browser` container entry point; streams headless Chromium viewports to cockpit viewers. |
| Auth / magic link | `magic_link_server.py`, `magic_link_handler.py`, `oauth_device_flow.py`, `auth_flows/` (chatgpt.py, claude.py) | Standalone auth-email interception and headless OAuth re-auth. |
| Scraping / outreach | `overnight_scrape.py` (252), `icp_scorer.py` (603) | The `os-scraper` container entry point and ICP lead scoring. |
| Trackers / trivia | `cost_tracker.py` (414), `kpi_tracker.py` (411), `heartbeat.py`, `goal_api.py`, `higgsfield_webhook.py`, `trigger_export.py`, `tier_3_fallback.py` | Cost/KPI tracking, heartbeat, goal REST, misc entry points. |
| `auth_flows/` | 3 | Scripted login flows for ChatGPT and Claude (Playwright). |

### Docker service topology
`docker-compose.yml` defines six containers, each launching one entry point (CPU caps
are the layer-3 defense in the CPU-gate stack):

| Container | Launches | CPU cap |
|---|---|---|
| `os-scraper` | `services/overnight_scrape.py` | 0.25 |
| `os-webhook` | `transports/api/webhooks/calendly_webhook.py` | 0.25 |
| `os-discord` | `services/discord_bot.py` | 0.35 |
| `os-livekit` | LiveKit server (`--config /etc/livekit.yaml`) | 0.35 |
| `os-browser` | `services/browser_relay.py` | 0.50 |
| `os-operator` | `uvicorn services.operator_api:app` on `:8091` | 1.00 |

Note that one container (`os-webhook`) launches a `transports/` module, and the mesh
WebSocket server (`transports/node_mesh/`) runs as a host process outside Docker — the
container list is not the whole runtime. See [services-runtime.md](../services-runtime.md)
for the complete process/host/cron picture.

## Key components
- **`services/discord_bot.py` (1,915 lines)** — the primary transport's process, the
  `os-discord` container. It imports its handlers from `transports/presence/`
  (`intent_handler`, `cc_command_handler`, `substrate_command_handler`,
  `pipeline_handler`) and its posting utilities from `transports/discord/`. A graph
  entry point.
- **`services/operator_api.py` (809 lines)** — the operator workstation API served by
  `os-operator`. (There is a parallel `transports/api/operator.py` with the same
  docstring — the migrated location; verify which is live before editing.)
- **`services/browser_relay.py` (583 lines)** — the `os-browser` viewport streamer; a
  graph entry point.
- **`services/cost_tracker.py` / `kpi_tracker.py`** — the trackers that write the JSON
  logs described below.

## Data & state
- **Runtime JSON logs live here alongside the code**: `calls_log.json`,
  `cost_log.json`, `revenue_log.json`, `kpi_history.json`, `opener_stats.json`,
  `scraped_posts.json`, `instagram_session.json`, plus config
  (`hashtag_config.json`, `export_profiles.yaml`). These are runtime state committed
  into a code directory — by node-role discipline and the "no runtime intermediaries"
  rule they arguably belong under `logs/` or `data/`, not `services/`.
- **Secrets**: `services/.env` and `.env.tpl` / `mesh.env.tpl` resolve from 1Password at
  runtime (`op run --env-file`); never commit raw secret values.
- **`bridge_health.py`** watches the Windows bridge from the VPS side.

## Gotchas
- **Deployment entrypoints only — but reality diverges.** `services/CLAUDE.md` marks
  this a legacy directory being migrated; three Discord files carry heavy handler logic
  and `discord_bot_commands.py` (3,113 lines) exceeds the 3,000-line ceiling. This is
  tracked migration debt, not new code to extend — add new surfaces in `transports/`.
- **Docker runs Python 3.11.** No 3.12+ syntax (no backslash in f-string expressions,
  etc.) in anything a container executes.
- **Restart by container name.** Use `docker restart os-discord` (the `container_name`),
  not `docker compose restart` which uses the compose alias. After code changes to
  `services/`, restart the affected container and verify clean startup from `docker logs`.
- **Never restart all services at once** — follow the deploy-service decision tree, and
  never rebuild Docker for Python-only changes.
- **The mesh server is not a container.** `transports/node_mesh/` runs on `:8094` as a
  host process; a Docker restart does not touch it.
- **CPU gate.** `services/` is exempt from the raw-subprocess pre-commit gate, but the
  container CPU caps above are load-bearing — they are layer 3 of the 6-layer CPU
  defense that exists because Hostinger throttled the VPS for a week after a runaway
  process.
- **Two `operator_api` surfaces exist** (`services/operator_api.py` and
  `transports/api/operator.py`); confirm which one the running container serves before
  changing either.

## See also
- [services-runtime.md](../services-runtime.md) — full runtime process/host/cron topology
- [dirs/transports.md](transports.md) — where handler logic and new surfaces live
- [dirs/adapters.md](adapters.md) — `register_all_sockets()`, called at service startup
- [dirs/substrate.md](substrate.md) — the governed core services delegate into
- [architecture.md](../architecture.md) · [tech-stack.md](../tech-stack.md)
