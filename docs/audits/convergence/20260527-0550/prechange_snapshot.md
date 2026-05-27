# UMH Coherence Convergence — Pre-Change Snapshot

**Date:** 2026-05-27 05:50 UTC
**Branch:** chore/umh-coherence-convergence-20260527-0550
**Operator:** Developer Agent (Claude Code)

---

## Git Status

Clean worktree (fresh checkout from main at cb320542).
Main branch has untracked files (runtime data, audits, archive) — all gitignored or intentionally untracked.

## Docker Containers

| Container    | Status                       | Ports                |
|-------------|------------------------------|----------------------|
| os-discord  | Up 11 hours                  | 0.0.0.0:8765->8765   |
| os-webhook  | **Restarting (crash loop)**  | (8080 mapped)        |
| os-operator | Up 4 hours                   | 0.0.0.0:8091->8091   |

**os-webhook crash cause:** `KeyError: 'EOS_ORG_ID'` — compose only loads `services/.env`, missing `infra/docker/umh.env`.

## Docker Compose Services

- os-discord
- os-operator
- os-scraper
- os-webhook

## Active Listening Ports

| Port  | Process         | Notes                              |
|-------|-----------------|-------------------------------------|
| 8888  | node            | code-server                         |
| 631   | cupsd           | CUPS print (system)                 |
| 8765  | docker-proxy    | os-discord WebSocket                |
| 56996 | tailscaled      | Tailscale                           |
| 2019  | caddy           | Caddy admin                         |
| 5199  | node            | (saas/cockpit dev?)                 |
| 8091  | docker-proxy    | os-operator API                     |
| 8094  | python3         | **umh-mesh (backlog: 101)**         |
| 7681  | ttyd            | Terminal web                        |
| 53    | systemd-resolve | DNS                                 |
| 80    | caddy           | HTTP reverse proxy                  |
| 11434 | ollama          | Ollama API                          |

**Critical:** Port 8094 (mesh) has accept backlog of 101 — at or near capacity.

## Systemd Services

- `umh-mesh.service` — **active (running)** since 2026-05-26 14:15:23 PDT
  - PID 92147, 1.9M memory, 318ms CPU
  - Windows desktop node connected and registered
  - Command: `/usr/bin/python3 /opt/OS/transports/node_mesh/run.py`

## Crontab (30 entries)

### Every 5 minutes (staggered)
- day_reminder.py
- agent_task_executor.py
- orchestrator_loop.py
- auth_monitor/health_check.sh
- auth_monitor/session_resurrector.sh

### Every 15 minutes (staggered)
- call_prep.py
- notion_tasks_sync.py
- post_meeting_capture.py
- calendar_invite_handler.py
- noshow_detector.py
- notion_sync_poller.py

### Every 30 minutes
- sync_all.sh --pull

### Every 6 hours
- cc_keepalive.sh

### Nightly (2-4am)
- nightly_maintenance.sh
- discord_daily_clear.py
- emit_signal.py nightly_cycle
- os-scraper (docker compose)

### Morning sequence (5:30-6:10am)
- emit_signal.py morning_ready
- morning_intel.py
- orchestrator.py
- waiting_on_checker.py
- deadline_monitor.py

### Daytime
- midday_checkin.py (12:30)
- inbox_gps_afternoon.py (15:00)
- eod_sync.py (18:00)

### Weekly
- emit_signal.py weekly_cycle
- portfolio_brief.py
- relationship_nurture.py
- weekly_review.py
- week_architect.py

### Continuous
- tailscale status → JSON (every minute)

## Disk Usage

| Path                  | Size  |
|-----------------------|-------|
| /opt/OS total         | 609M  |
| .git                  | 112M  |
| data/                 | 391M  |
| saas/node_modules     | 114M  |
| Filesystem /          | 74G/96G (77%) |

## Environment Files (key names only)

### services/.env (40+ keys)
EOS_ORG_ID, EOS_USER_ID, DATABASE_URL, DISCORD_BOT_TOKEN, ANTHROPIC_API_KEY,
APIFY_API_TOKEN, CALENDLY_SIGNING_KEY, EOS_PORTFOLIO_ID, FOUNDER_DISCORD_ID,
plus Discord channel/webhook IDs, router config, bridge config.

### infra/docker/umh.env (40+ keys)
EOS_ORG_ID, EOS_USER_ID, DATABASE_URL, ANTHROPIC_API_KEY, GEMINI_API_KEY,
GROQ_API_KEY, HIGGSFIELD_API_KEY, NOTION_API_KEY, plus ~30 Notion DB IDs,
bridge config, portfolio/task config.

### Env loading by service
| Service     | services/.env | umh.env | Compose env overrides |
|-------------|:---:|:---:|:---:|
| os-discord  | ✓ | ✓ | ✓ |
| os-operator | ✓ | ✓ | ✓ |
| os-scraper  | ✓ | ✓ | ✓ |
| os-webhook  | ✓ | **✗** | ✓ |

**Root cause of os-webhook crash:** Missing `infra/docker/umh.env` in env_file list.

## Top-Level Directory Structure

```
substrate/       — UMH brain (18 subdirs)
adapters/        — external adapters (11 subdirs)
transports/      — I/O surfaces
projections/     — eos, creatoros, lyfeos
services/        — deployment entrypoints
nodes/           — distributed execution
cockpit/         — operator UI
saas/            — SaaS backend
scripts/         — operational scripts
skills/          — TME skills
knowledge/       — wiki, palace, concepts
docs/            — architecture, audits
data/            — runtime state, proofs
agents/          — agent soul docs
```

## Known Issues at Snapshot Time

1. **os-webhook crash-looping** — missing EOS_ORG_ID env var
2. **Mesh backlog 101** — port 8094 accept queue full
3. **77% disk** — manageable but monitor
4. **30 cron jobs** — some may reference stale scripts
5. **No secrets exposed** in this snapshot ✓
