# Existing Local Daemon Discovery v1

**Date**: 2026-05-04
**Phase**: 93R.0 — Existing Local Daemon Discovery + Reconnection v1
**Purpose**: Find and document every existing daemon, worker, and bridge mechanism that connects the VPS to a local workstation.

---

## Discovery Summary

Two distinct systems exist for VPS ↔ Local communication. Both are code-complete and were operational as recently as 2026-05-02.

| System | Purpose | Transport | Status |
|--------|---------|-----------|--------|
| **Local Bridge** (services/) | Discord ↔ local Claude Code session routing | HTTP over Tailscale | LIKELY_ACTIVE (env enabled, code intact) |
| **Station Daemon** (eos_ai/substrate/) | Substrate action dispatch to local workstation | File bus (JSON) + HTTP transport | STALE_RISK (last log 2026-05-02, heartbeat stale events in log) |

---

## 1. Files Found

### Local Bridge System (services/)

| # | Path | Summary | Confidence | Relevance | Active/Stale |
|---|------|---------|-----------|-----------|-------------|
| 1 | `services/local_bridge_client.py` | VPS-side HTTP client. `forward_to_local()` checks health then POSTs `{text, session_name}` to local machine. Returns `False` for graceful fallback. | CONFIRMED | HIGH — this is the VPS → local forwarding mechanism | ACTIVE — env vars enabled, code referenced |
| 2 | `services/local_bridge_server.py` | Local-side (Windows WSL) HTTP server. Receives messages, injects into local tmux CC sessions via `tmux send-keys`. Fallback: writes to `~/eos_inbox/{session}.txt`. | CONFIRMED | HIGH — this is what runs on the local machine | NEEDS_LOCAL_VERIFICATION — only exists on VPS as a copy |
| 3 | `services/local_bridge_send_to_discord.sh` | CC Stop hook script. Reads last assistant message from JSONL transcript, POSTs to VPS webhook receiver. Installed on local WSL as `~/.claude/hooks/send-to-discord.sh`. | CONFIRMED | HIGH — reply path from local CC → Discord | NEEDS_LOCAL_VERIFICATION |
| 4 | `services/cc_webhook_receiver.py` | VPS-side webhook receiver. Maps `session_name` → Discord `channel_id`. Handles `/cc-reply` and `/cc-prompt`. Started as background task inside `discord_bot.py`'s `on_ready`. | CONFIRMED | HIGH — reply path endpoint on VPS | LIKELY_ACTIVE — part of os-discord container |
| 5 | `services/LOCAL_BRIDGE_SETUP.md` | Complete setup guide. Architecture diagram, VPS config, WSL setup (6 steps), troubleshooting, security notes. | CONFIRMED | HIGH — operational documentation | CURRENT |
| 6 | `tools/local_bridge_client.py` | Duplicate copy of `services/local_bridge_client.py` (4116 bytes, dated Apr 25). | CONFIRMED | LOW — duplicate | STALE (older copy) |

### Station Daemon System (eos_ai/substrate/)

| # | Path | Summary | Confidence | Relevance | Active/Stale |
|---|------|---------|-----------|-----------|-------------|
| 7 | `eos_ai/substrate/station_daemon.py` | Full daemon implementation (859 lines). Polls StationBus outbox, executes MVP-safe actions (PLAY_SOUND, SPEAK_TEXT, OPEN_URL, LAUNCH_APP, OPEN_SCENE, FOCUS_APP), posts results to inbox, emits heartbeats. CLI: `python3 -m eos_ai.substrate.station_daemon --node-id antony-workstation`. | CONFIRMED | MEDIUM — action execution daemon, not message routing | STALE_RISK — heartbeat stale events in workstation.jsonl |
| 8 | `eos_ai/substrate/station.py` | Station contract. Defines `StationHeartbeat`, `StationEvent`, `ControlMode` (OBSERVE/ASSIST/DRIVE). Protocol/schema only, no daemon implementation. | CONFIRMED | MEDIUM — protocol layer | ACTIVE (imported by daemon) |
| 9 | `eos_ai/substrate/station_bus.py` | File-based transport. Per-node JSON inbox/outbox files in `eos_ai/.substrate_station/`. Atomic writes via tempfile + os.replace. | CONFIRMED | MEDIUM — substrate transport | ACTIVE (files present) |
| 10 | `eos_ai/substrate/node_transport.py` | HTTP transport adapter. `NodeTransportServer` serves `/node/heartbeat`, `/node/task`, `/node/status`, `/node/health` on port 7600. Additive alongside file bus. | CONFIRMED | MEDIUM — HTTP transport option | ACTIVE (code exists, additive) |
| 11 | `eos_ai/substrate/local_listener.py` | Bounded activation layer. Accepts `LocalTrigger` (manual, hotkey, wake word, clap, scheduled). Gates through readiness + ritual policy. 397 lines. | CONFIRMED | LOW — activation triggers, not task routing | ACTIVE |
| 12 | `eos_ai/substrate/execution_worker.py` | Event-driven execution handler. Bridges requests to adapters. Subscribes to `execution_requested` events. | CONFIRMED | LOW — substrate execution, not local bridge | ACTIVE |
| 13 | `eos_ai/substrate/control_bridge.py` | File-backed command queue per node. `ControlCommand` envelopes. No networking, no daemons, no auto-dispatch. | CONFIRMED | LOW — command queue, substrate layer | ACTIVE |
| 14 | `eos_ai/substrate/task_queue.py` | Priority queue for task system. CRITICAL/HIGH/NORMAL/LOW. `operator_blocked`, `autonomous_day`, `approval_waiting` queues. | CONFIRMED | LOW — task prioritization | ACTIVE |
| 15 | `eos_ai/substrate/claude_session_bridge.py` | 40KB. Bridges Claude Code sessions to Discord. Manages tmux session injection, prompt forwarding, response capture. | CONFIRMED | MEDIUM — session bridge layer | ACTIVE |
| 16 | `eos_ai/substrate/session_watcher.py` | One `SessionWatcher` per tmux session. Monitors CC state (plan mode, permission, question). Emits `WatcherEvent`. | CONFIRMED | MEDIUM — session monitoring | ACTIVE |
| 17 | `eos_ai/substrate/session_discord_bridge.py` | Formats `WatcherEvent` into Discord messages with interactive buttons. | CONFIRMED | MEDIUM — Discord UI layer | ACTIVE |
| 18 | `eos_ai/substrate/remote_executor.py` | Remote execution adapter (8076 bytes). | CONFIRMED | LOW | ACTIVE |

---

## 2. Scripts Found

| # | Path | Summary | Relevance |
|---|------|---------|-----------|
| 1 | `scripts/auth_monitor/credential_watcher.sh` | Monitors credential state | LOW |
| 2 | `scripts/auth_monitor/cc_keepalive.sh` | CC session keepalive | MEDIUM |
| 3 | `scripts/auth_monitor/session_resurrector.sh` | Resurrects dead sessions | MEDIUM |
| 4 | `scripts/auth_monitor/credential_coordinator.sh` | Credential rotation | LOW |
| 5 | `scripts/auth_monitor/setup_isolation.sh` | Auth isolation setup | LOW |
| 6 | Multiple `scripts/substrate_*_smoke_test.py` | Smoke tests for substrate components | LOW |
| 7 | `scripts/substrate_session_orchestration_cli.py` | Session orchestration CLI | MEDIUM |
| 8 | `scripts/substrate_claude_session_cli.py` | Claude session CLI | MEDIUM |

---

## 3. Services / Cron / Tmux References

### Active tmux sessions (VPS)

| Session | Created | Status |
|---------|---------|--------|
| `dex_main` | 2026-04-29 | Running |
| `umh_core` | 2026-04-29 | Running, attached |
| `umh_tests` | 2026-04-29 | Running, attached |
| `umh_worker` | 2026-04-29 | Running, attached |

### Cron entries (VPS)

No cron entries specifically for the local bridge or station daemon. The bridge is event-driven (triggered by Discord messages), not scheduled.

### Docker containers

`os-discord` container runs `discord_bot.py` which starts `cc_webhook_receiver.py` in `on_ready`. This is the VPS-side reply receiver for the local bridge.

---

## 4. Queue / Polling Mechanisms

| # | Mechanism | Location | Type | Status |
|---|-----------|----------|------|--------|
| 1 | **StationBus file bus** | `eos_ai/.substrate_station/*.json` | JSON file polling (1s interval) | ACTIVE — inbox/outbox files present for `antony-workstation` |
| 2 | **HTTP health check** | `local_bridge_client.py → GET /health` | HTTP poll (2s timeout) | ACTIVE — env vars enabled |
| 3 | **Inbox file fallback** | `local_bridge_server.py → ~/eos_inbox/` | File write, manual pickup | NEEDS_LOCAL_VERIFICATION |
| 4 | **Task queue** | `eos_ai/substrate/task_queue.py` | Priority queue over TaskStore | ACTIVE (code, not local-specific) |
| 5 | **Control bridge queue** | `eos_ai/substrate/control_bridge.py` | File-backed command queue per node | ACTIVE (code, bounded to 100/node) |

### Substrate station bus files (VPS)

```
eos_ai/.substrate_station/antony-workstation.inbox.json   — 2 bytes (empty [])
eos_ai/.substrate_station/antony-workstation.outbox.json  — 2 bytes (empty [])
```

Both are empty — no pending actions or results.

---

## 5. Local / VPS Sync References

| # | Mechanism | Direction | Transport | Status |
|---|-----------|-----------|-----------|--------|
| 1 | `forward_to_local()` | VPS → Local | HTTP POST over Tailscale (100.74.199.102:8766) | LIKELY_ACTIVE |
| 2 | `send-to-discord.sh` | Local → VPS | HTTP POST over Tailscale (100.77.233.50:8765) | NEEDS_LOCAL_VERIFICATION |
| 3 | StationBus file sync | Bidirectional | `tailscale file cp` or shared filesystem | UNKNOWN — no evidence of automated file sync |
| 4 | `scp` / `git pull` | Manual sync | SSH / Git over Tailscale | CONFIRMED — in LOCAL_BRIDGE_SETUP.md |

### Tailscale IPs

| Machine | IP | Role |
|---------|-----|------|
| VPS | 100.77.233.50 | Primary orchestrator node |
| Local PC (Windows/WSL) | 100.74.199.102 | Local workstation bridge |

---

## 6. Approval / Governance References

| # | Mechanism | Location | Description |
|---|-----------|----------|-------------|
| 1 | **Founder approval list** | `initiate_arena_execution_context_v1.md` §10 | 6 actions requiring founder approval before execution |
| 2 | **authority_engine.py** | `eos_ai/authority_engine.py` | 4 risk classes (LOW/MEDIUM/HIGH/CRITICAL) |
| 3 | **ControlMode** | `eos_ai/substrate/station.py` | OBSERVE/ASSIST/DRIVE — trust levels |
| 4 | **MVP_ALLOWED_ACTIONS** | `eos_ai/substrate/station.py` | Frozenset of 6 allowed action kinds |
| 5 | **StationContract.propose()** | `eos_ai/substrate/station.py` | Rejects action kinds not in MVP allow-list |
| 6 | **approval_waiting queue** | `eos_ai/substrate/task_queue.py` | Queue name for tasks awaiting approval |
| 7 | **CC prompt handler** | `services/cc_webhook_receiver.py` `/cc-prompt` | Sends permission/plan/question prompts to Discord with interactive buttons |

---

## 7. Logs Found

| # | Path | Size | Last Modified | Content |
|---|------|------|---------------|---------|
| 1 | `logs/workstation.jsonl` | 177 KB | 2026-05-02 15:35 | Node events: `tmux_session_missing`, `node_degraded`, `session_opened`, `session_closed`, `resume_decision` |
| 2 | `logs/workstation.jsonl.1` | 5.2 MB | 2026-04-28 01:29 | Rotated log — older events |

### Log analysis

**Earliest entry examined**: 2026-04-28 08:29 — `tmux_session_missing` for `dex_product_main`
**Latest entry examined**: 2026-05-02 22:35 — `session_opened` / `session_closed` / `resume_decision`
**Key patterns**:
- Frequent `tmux_session_missing` events → local tmux sessions not always running
- Periodic `node_degraded` with reason "heartbeat stale" → daemon heartbeat lapsing
- `session_opened` / `session_closed` events with `transport: "discord"` → active Discord-side session management
- Node ID consistently `antony-workstation`

---

## 8. Unknowns

| # | Unknown | Impact | How to Resolve |
|---|---------|--------|---------------|
| 1 | Is `local_bridge_server.py` currently running on Windows WSL? | Blocks: if not running, VPS health check fails and all messages stay on VPS | Check from VPS: `curl http://100.74.199.102:8766/health` |
| 2 | Is the CC Stop hook installed on the local machine? | Blocks: replies from local CC won't reach Discord | Check `~/.claude/settings.json` on local WSL |
| 3 | Are local tmux sessions (`dex_builder_main`, `dex_product_main`) running? | Blocks: bridge server falls back to inbox files | Check on local machine: `tmux list-sessions` |
| 4 | Is `discord_bot.py` integrating `local_bridge_client.forward_to_local()`? | Critical: no grep hits in discord_bot.py for forward_to_local | Read discord_bot.py message handler path |
| 5 | Is `local_bridge_server.py` up to date on the local machine? | Risk: local copy may be older than VPS copy | Compare file dates |
| 6 | Does the station daemon run on the local machine independently? | Determines: whether substrate actions reach the workstation | Check on local machine |
| 7 | Is Tailscale connected between VPS and local PC right now? | Blocks: all communication | `tailscale status` on both machines |
| 8 | How does the file bus (station_bus.py) sync between VPS and local? | The bus writes to VPS-local files. Unclear if `tailscale file cp` is automated or manual. | Check for any cron or daemon that syncs `.substrate_station/` to local |
| 9 | Is `forward_to_local()` actually called anywhere in the message handling path? | CRITICAL: grep found zero hits in `discord_bot.py` or handlers/ | Full code path analysis needed |

---

## 9. Evidence Paths

| Evidence | Path | What It Proves |
|----------|------|---------------|
| Bridge env vars enabled | `eos_ai/.env` + `services/.env` → `EOS_LOCAL_BRIDGE_ENABLED=1` | VPS is configured to attempt local bridge routing |
| Bridge client code | `services/local_bridge_client.py` (134 lines, production quality) | VPS-side forwarding is code-complete |
| Bridge server code | `services/local_bridge_server.py` (243 lines, production quality) | Local-side receiving is code-complete |
| Reply hook code | `services/local_bridge_send_to_discord.sh` (103 lines) | Local → VPS reply path is code-complete |
| Webhook receiver code | `services/cc_webhook_receiver.py` (240 lines) | VPS reply endpoint is code-complete |
| Setup documentation | `services/LOCAL_BRIDGE_SETUP.md` (162 lines) | Architecture fully documented |
| Station daemon code | `eos_ai/substrate/station_daemon.py` (859 lines) | Substrate daemon is code-complete |
| Station bus files | `eos_ai/.substrate_station/antony-workstation.*.json` | Bus files exist (empty) |
| Workstation log | `logs/workstation.jsonl` (177KB, last entry 2026-05-02) | System was logging workstation events 2 days ago |
| Session events | Last log entry: `session_opened` at 2026-05-02 22:35 | Session management was active on May 2 |
| Tailscale IPs hardcoded | Multiple files reference 100.74.199.102 (local) and 100.77.233.50 (VPS) | Network topology is known and stable |
| GWS Scanner exists | `eos_ai/gws_scanner.py` (Google Workspace document scanner) | Google Drive scanning capability exists on VPS |
| GWS Connector exists | `eos_ai/gws_connector.py` (calendar, tasks, drive, gmail via CLI) | Google Workspace API access exists on VPS |
