---
type: codewiki-page
title: Services & Runtime
---

# Services & Runtime — what is actually running

This page is the ground-truth map of the *live* system: the Docker containers, the host
processes that run **outside** Docker, the cron schedule, the systemd units, the Fly.io
cockpit deployment, and the LLM fallback chain. Everything below is verified against the
running VPS, not inferred from config.

## Live container snapshot (2026-07-10, VPS `srv1500858`)

```
NAMES         STATUS
os-operator   Up 21 minutes (healthy)
os-browser    Up 11 days
os-discord    Up 2 hours
os-livekit    Up 4 weeks
os-webhook    Up 11 days
```

Five containers running. `os-scraper` is defined in `docker-compose.yml` but is a **one-shot
nightly job** (`restart: "no"`), so it is correctly absent from `docker ps` — it runs via
cron `docker-compose run --rm os-scraper` at 04:00 and exits.

## Docker services (repo-root `docker-compose.yml`)

All six services run on the `eos_network` bridge, each with a hard CPU/memory cap enforcing
the CPU Gate Law (UMH must never saturate host CPU):

| Service / container | Command | CPU / mem cap | Restart | Ports | Role |
|---|---|---|---|---|---|
| `os-discord` | `services/discord_bot.py` | 0.35 / 1G | on-failure | 127.0.0.1:8765 | Primary conversational interface; mounts host `/tmp/tmux-0` to reach the `dex_main` CC session and `/root/.claude` read-only |
| `os-operator` | `uvicorn services.operator_api:app --port 8091` | 1.00 / 2G | unless-stopped | 127.0.0.1:8091 | Operator workstation API + cockpit backend; **has healthcheck**; mounts `docker.sock` (ro), mesh SSH key, tailscaled.sock |
| `os-webhook` | `transports/api/webhooks/calendly_webhook.py` | 0.25 / 128M | always | 127.0.0.1:8080 | Inbound Calendly/media webhook receiver |
| `os-browser` | `services/browser_relay.py` | 0.50 / 1280M | unless-stopped | 127.0.0.1:8086 | Playwright browser relay, 512m shm |
| `os-livekit` | `livekit/livekit-server:v1.8.3` | 0.35 / 256M | unless-stopped | 7880/7881/3478udp/50000-50020udp | WebRTC voice server; config bind-mounted from `infra/livekit.yaml` |
| `os-scraper` | `services/overnight_scrape.py` | 0.25 / 256M | **no** | — | One-shot nightly scraper (cron-invoked) |

`os-operator`'s memory cap was raised from 1G to 2G after 1G caused cgroup thrash under
sustained cockpit polling (idle RES ≈940 MiB pinned the cap). All service containers
bind-mount `${UMH_ROOT:-/opt/OS}` into `/app`, so **the live checkout is the source of the
running code** — a `docker restart` picks up Python edits without a rebuild.

## Host processes OUTSIDE Docker

Two long-lived processes run directly on the VPS host under systemd, not in any container.
`docker restart` never touches them — this is a repeated source of confusion:

| Process | Port | Unit | What it is |
|---|---|---|---|
| Node mesh server (`transports/node_mesh/run.py`) | :8094 | `umh-mesh.service` | The mesh WS/HTTP relay that dispatches work to executor nodes (the Beast). Wrapped in `op_run.sh` with `services/mesh.env.tpl` for 1Password secret injection. Verified LISTEN on 0.0.0.0:8094 |
| Vision relay (`umh/vision_relay.py`) | :8097 | `umh-vision-relay.service` | Bridges the Beast camera to cockpit viewers; self-installs iptables ACCEPT rules for :8097 from the Docker + localhost subnets. Verified LISTEN on 0.0.0.0:8097 |

There is also a **`dex_main` tmux CC session** on the host — a persistent Claude Code session
the router's `claude_cli` backend reaches via the mounted tmux socket. The Discord and
operator containers mount `/tmp/tmux-0` precisely to talk to it (`UMH_ROUTER_CLAUDE_CLI_TARGET=vps`,
`UMH_ROUTER_CLAUDE_CLI_SESSION=dex_main`).

## Cron schedule (`infra/crontab.managed`)

Every job is wrapped in `scripts/cron-run`, which provides `flock` (no overlapping runs),
`nice -n 15` + `ionice -c 3`, a 240s `timeout`, a CPU-load gate (skip if overloaded), and
1Password secret injection. Install with `crontab /opt/OS/infra/crontab.managed`.

- **Every 5 min (staggered):** `day_reminder.py`, `agent_task_executor.py`,
  `orchestrator_loop.py --cycles 1`, `auth_monitor/health_check.sh`,
  `auth_monitor/session_resurrector.sh`
- **Every 15 min (staggered):** `call_prep.py`, `notion_tasks_sync.py`,
  `post_meeting_capture.py`, `calendar_invite_handler.py`, `noshow_detector.py`,
  `notion_sync_poller.py`
- **Every 30 min:** `sync_all.sh --pull`
- **Every 6 h:** `auth_monitor/cc_keepalive.sh`
- **Nightly (02:00–04:00):** `nightly_maintenance.sh`, `discord_daily_clear.py`,
  `emit_signal.py nightly_cycle`, `rotate_jsonl.py`, and `docker-compose run --rm os-scraper`
- **Monthly (1st, 05:00):** `rotate_secrets.sh` under `op run`
- **Weekly (Sun 06:00):** `op audit events list` → 1Password audit log

The op service-account token is loaded by `cron-run` from `/root/.op-service-account-token`
and is **never inlined** in the crontab (it would leak via `crontab -l`).

## systemd units

`umh-mesh.service` and `umh-vision-relay.service` are the two host-process units (above).
The repo copies under `infra/systemd/` and `infra/umh-vision-relay.service` are **staged
copies** — the live units are in `/etc/systemd/system/`. Applying a change requires
`sudo cp … && systemctl daemon-reload && systemctl restart`.

## Fly.io cockpit deployment

The operator cockpit frontend deploys to **Fly.io** as the `umh-cockpit` app, served at
`universalmetaharness.tech` (the single canonical domain — never `umh-cockpit.fly.dev`).
Deployment is gated: **always `bash cockpit/deploy.sh`, never `flyctl deploy` directly**
(Cockpit Deploy Gate law). The gate verifies `nginx.conf.template`, `Dockerfile`, and
`start.sh` match `main` before shipping, preventing a worktree/branch deploy from shipping
stale auth config (a past worktree deploy shipped without API-key injection → 401 on every
cockpit API call). The gate also kills the flyctl agent first to avoid stale-cache deploys.
The mobile builds of the cockpit are produced by [`.github/workflows/mobile-build.yml`](dirs/dot-github.md);
CI only builds artifacts, it does not deploy.

## LLM fallback chain

All model calls route through `adapters/models/model_router.py::call_with_fallback()` (the
single module-level entry point). The provider chain, in order:

```
cc_sdk (Opus 4.8 via Claude Code CLI / Max subscription — option 0, no API cost)
  → Gemini 2.5 Flash
  → Groq
  → Ollama (local fallback: qwen2.5:0.5b tiny on VPS; qwen2.5-coder:14b on the Beast :11434)
```

Each provider follows the contract "return None/empty on failure, non-empty content on
success." `cc_sdk` validates its output against error signatures (`_is_error_leak()`) and
returns None on auth/quota/transport leaks so the router falls through. CEO/strategic calls
force the best model (`agent_type='ceo'` or `force_opus=True`). When Anthropic API credits are
restored, the chain becomes Anthropic (CC_MODEL_MAP) → Gemini → Ollama. Per the
Deterministic-First Principle, every LLM call must degrade to a deterministic fallback — the
system must still produce output with all providers down.

## Gotchas
- **The mesh (:8094) and vision relay (:8097) are host processes, not containers** — restart
  them with `systemctl`, never `docker restart`.
- **`os-scraper` absent from `docker ps` is correct**, not a failure — it is a one-shot cron
  job (`restart: "no"`).
- **Editing `/opt/OS` changes running services** (bind-mounted). Branch/commit only in a
  worktree; the live checkout is the containers' file source.
- Cockpit deploys **only** through `cockpit/deploy.sh`; a direct `flyctl deploy` bypasses the
  auth-config verification gate.
- Use `docker restart <container_name>` (e.g. `docker restart os-operator`), not
  `docker compose restart` — the compose service alias and the `container_name:` differ.

## See also
- [`_root-files`](dirs/_root-files.md) — the `docker-compose.yml` that defines these services
- [`infra/`](dirs/infra.md) — cron, systemd units, device/service registries, livekit config
- [`services/`](dirs/services.md) — the entrypoint modules (`discord_bot.py`, `operator_api.py`, …)
- [`docker/`](dirs/docker.md) — the Beast computer-use container
- [architecture](architecture.md) · [tech-stack](tech-stack.md) · [data-flow](data-flow.md)
