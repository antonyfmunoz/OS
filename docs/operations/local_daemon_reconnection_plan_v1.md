# Local Daemon Reconnection Plan v1

**Date**: 2026-05-04
**Phase**: 93R.0 — Existing Local Daemon Discovery + Reconnection v1
**Purpose**: Document what the existing daemon does, how to reconnect it safely, and what to verify on the local machine.

---

## Confidence Legend

| Tag | Meaning |
|-----|---------|
| CONFIRMED | Code and documentation agree, evidence is direct |
| LIKELY | Strong evidence from code/logs but needs local verification |
| UNKNOWN | No evidence found, cannot determine from VPS alone |
| STALE_RISK | Was working but may have drifted or stopped |
| NEEDS_LOCAL_VERIFICATION | Can only be confirmed from the local machine |

---

## 1. What the Existing Daemon Appears to Do

Two separate systems were found. They serve different purposes and can operate independently.

### System A: Local Bridge (Discord Message Routing)

| Aspect | Finding | Confidence |
|--------|---------|-----------|
| **Purpose** | Routes Discord messages to a Claude Code session on the local PC when the founder is at his desk. Falls back to VPS when away. | CONFIRMED |
| **VPS side** | `local_bridge_client.py` checks health of local machine → if healthy, POSTs message with `{text, session_name}` to local server. If unhealthy, message stays on VPS. | CONFIRMED |
| **Local side** | `local_bridge_server.py` (aiohttp) receives POST, injects text into local tmux CC session via `tmux send-keys`. Falls back to writing to `~/eos_inbox/{session}.txt`. | CONFIRMED |
| **Reply path** | CC Stop hook (`send-to-discord.sh`) reads last assistant message from JSONL transcript, POSTs to VPS webhook receiver → Discord. | CONFIRMED |
| **Env vars** | `EOS_LOCAL_BRIDGE_ENABLED=1` in both `.env` files on VPS | CONFIRMED |
| **Integration point** | `discord_bot.py` should call `forward_to_local()` but no grep hits were found in the message handling path | UNKNOWN — CRITICAL GAP |

### System B: Station Daemon (Substrate Action Execution)

| Aspect | Finding | Confidence |
|--------|---------|-----------|
| **Purpose** | Executes EOS substrate actions on the local workstation (play sounds, speak text, open URLs, launch apps, open scenes, focus apps) | CONFIRMED |
| **Transport** | Polls StationBus outbox files (`eos_ai/.substrate_station/antony-workstation.outbox.json`) every 1s. Also serves HTTP on port 7600 (additive). | CONFIRMED |
| **Heartbeat** | Emits heartbeat every 15s via NodeRegistry + StationEvent. Heartbeats visible in `logs/workstation.jsonl`. | CONFIRMED |
| **Action safety** | Only 6 MVP-allowed actions. No raw shell, no browser automation, no window control. | CONFIRMED |
| **Last known activity** | `logs/workstation.jsonl` shows events through 2026-05-02 22:35. Frequent `heartbeat stale` and `tmux_session_missing` events in the log. | STALE_RISK |
| **File sync** | Station bus files are on VPS only. No evidence of automated sync to local machine. The daemon would need to run on VPS (co-located with bus files) or have a sync mechanism. | UNKNOWN |

---

## 2. How VPS Likely Communicates with Local PC

```
                   TAILSCALE PRIVATE NETWORK
                   ========================
                   
VPS (100.77.233.50)                Local PC (100.74.199.102)
┌────────────────────┐             ┌────────────────────┐
│                    │             │                    │
│ Discord message    │             │                    │
│ → discord_bot.py   │             │                    │
│ → forward_to_local │─── HTTP ───▶│ local_bridge_server│
│   (health check    │  POST       │ → tmux send-keys   │
│    + POST /message)│  :8766      │ → CC session       │
│                    │             │                    │
│ cc_webhook_receiver│◀── HTTP ────│ send-to-discord.sh │
│ ← /cc-reply        │  POST      │ (CC Stop hook)     │
│ → Discord channel  │  :8765      │                    │
│                    │             │                    │
└────────────────────┘             └────────────────────┘

Transport: HTTP over Tailscale (private network, no public exposure)
Security: No secrets transmitted, only message text + session names
Fallback: If local is unreachable, VPS handles everything locally
```

**Confidence**: CONFIRMED — full architecture documented in `LOCAL_BRIDGE_SETUP.md`

---

## 3. How Local PC Likely Receives Tasks

### For Discord messages (System A)

1. VPS `forward_to_local()` does `GET /health` with 2s timeout
2. If healthy → `POST /message` with `{text, session_name}`
3. Local server checks for tmux session → `tmux send-keys` injection
4. If no tmux session → writes to `~/eos_inbox/{session}.txt`

**Confidence**: CONFIRMED

### For substrate actions (System B)

The station daemon polls local files. But the files are on the VPS. Three possible sync methods:

1. **Co-located**: Daemon runs on VPS, not on local machine → LIKELY for development
2. **tailscale file cp**: Manual or scripted file sync → UNKNOWN, no cron evidence
3. **HTTP transport**: Node transport server on port 7600 bypasses file bus → CONFIRMED code exists, UNKNOWN if used

**Confidence**: UNKNOWN — cannot determine how file bus syncs without local verification

---

## 4. Where Work Orders / Results Should Go If Already Defined

| Data type | From | To | Mechanism | Path |
|-----------|------|----|-----------|------|
| Discord message text | VPS | Local | HTTP POST /message | `services/local_bridge_client.py` → `services/local_bridge_server.py` |
| CC reply text | Local | VPS | HTTP POST /cc-reply | `services/local_bridge_send_to_discord.sh` → `services/cc_webhook_receiver.py` |
| CC prompt (permission/plan) | Local | VPS | HTTP POST /cc-prompt | via webhook receiver → Discord buttons |
| Substrate SafeAction | VPS (bus outbox) | Local (daemon) | File bus or HTTP /node/task | `station_bus.py` → `station_daemon.py` |
| Action result | Local (daemon) | VPS (bus inbox) | File bus post | `station_daemon._post_result()` → `station_bus.daemon_post_result()` |
| Heartbeat | Local (daemon) | VPS | File bus event | `station_daemon._emit_heartbeat()` |

---

## 5. What Must Be Verified Manually on the Local PC

| # | Check | Command | Expected result | Why it matters |
|---|-------|---------|----------------|---------------|
| 1 | Tailscale connected | `tailscale status` | Shows VPS (100.77.233.50) as connected | All communication depends on this |
| 2 | Bridge server running | `curl http://localhost:8766/health` | `{"status": "ok", "machine": "local"}` | VPS → local routing depends on this |
| 3 | Tmux sessions exist | `tmux list-sessions` | Shows `dex_builder_main` or `dex_product_main` | Message injection target |
| 4 | CC Stop hook installed | `cat ~/.claude/settings.json` | Has Stop hook pointing to `send-to-discord.sh` | Reply path back to Discord |
| 5 | `send-to-discord.sh` exists | `ls -la ~/.claude/hooks/send-to-discord.sh` | File exists and is executable | Reply hook script |
| 6 | VPS webhook reachable from local | `curl http://100.77.233.50:8765/health` | Returns 200 | Reply path endpoint |
| 7 | Local bridge server is current version | `md5sum ~/local_bridge_server.py` | Matches VPS copy | File may be outdated |
| 8 | Station daemon running | `ps aux \| grep station_daemon` | Process found (or not) | Determines substrate action delivery |
| 9 | WSL aiohttp installed | `pip show aiohttp` | Package info shown | Bridge server dependency |
| 10 | `~/eos_inbox/` directory exists | `ls ~/eos_inbox/` | Directory exists | Fallback message storage |

---

## 6. Safe Reconnection Sequence

### Pre-flight (from VPS)

```
Step 1: Test Tailscale reachability
    tailscale ping 100.74.199.102
    Expected: reply within 1-2s

Step 2: Test bridge health  
    curl -s http://100.74.199.102:8766/health
    Expected: {"status": "ok", "machine": "local"}
    If fails: bridge server is not running on local → go to Local Setup below

Step 3: Test VPS webhook
    curl -s http://127.0.0.1:8765/health
    Expected: 200 ok (served by discord_bot container)
```

### Local Setup (if bridge server is not running)

```
Step 1: SSH to local WSL (or Termius from iPhone)
Step 2: Verify files exist:
    ls ~/local_bridge_server.py ~/send-to-discord.sh
Step 3: If missing, copy from VPS:
    scp root@100.77.233.50:/opt/OS/services/local_bridge_server.py ~/
    scp root@100.77.233.50:/opt/OS/services/local_bridge_send_to_discord.sh ~/send-to-discord.sh
Step 4: Start bridge server:
    tmux new-session -d -s bridge "python3 ~/local_bridge_server.py"
Step 5: Start CC session:
    tmux new-session -d -s dex_builder_main
    tmux send-keys -t dex_builder_main "claude" Enter
Step 6: Verify:
    curl http://localhost:8766/health
```

### Post-reconnection verification (from VPS)

```
Step 1: Health check
    curl -s http://100.74.199.102:8766/health

Step 2: Test message forwarding
    python3 -c "
    import sys; sys.path.insert(0, '/opt/OS')
    from services.local_bridge_client import forward_to_local
    print(forward_to_local('test message from VPS', 'dex_builder_main'))
    "
    Expected: True

Step 3: End-to-end test via Discord
    Send a message in the builder channel → should appear in local CC session
    Local CC reply → should appear back in Discord
```

---

## 7. What Not to Touch

| # | Don't touch | Why |
|---|-------------|-----|
| 1 | `services/discord_bot.py` | Production Discord bot — any edit affects live service |
| 2 | `eos_ai/substrate/station_daemon.py` | Working daemon code — reconnect, don't rewrite |
| 3 | `eos_ai/.substrate_station/` inbox/outbox files | Active bus state — corruption loses pending actions |
| 4 | `.env` files — `EOS_LOCAL_BRIDGE_ENABLED` | Already set to `1` (enabled) — don't toggle without testing |
| 5 | `services/cc_webhook_receiver.py` | Part of live os-discord container — don't modify |
| 6 | Cron entries | None are bridge-related — don't add new ones without planning |
| 7 | Docker containers | Don't restart `os-discord` unless necessary — it runs the webhook receiver |
| 8 | Local machine files | Don't overwrite without checking what's already there |

---

## 8. Next Work Order Adaptation

### What the bridge CAN currently carry

- Discord text messages → local CC session (inject + reply)
- Interactive prompts (permission, plan mode, questions) → Discord with buttons
- Session management (open, close, resume decisions)

### What the bridge CANNOT currently carry

- Arbitrary work orders (structured task payloads)
- Approval gates (work order → wait for approval → execute)
- File export results (local machine → VPS)
- Google Workspace navigation commands
- Structured evidence/result writeback

### To adapt for ingestion work orders

The existing bridge could be extended by:

1. Adding a `/work-order` endpoint to `local_bridge_server.py` (accepts structured JSON payloads)
2. Adding a `/work-order-result` endpoint to `cc_webhook_receiver.py` (receives results)
3. Using the existing approval queue pattern from `task_queue.py` for gating
4. Using the existing `ControlCommand` envelope from `control_bridge.py` as the work order format

**Or** the StationBus + StationDaemon could be extended with new action kinds (e.g., `READ_LOCAL_FILE`, `EXPORT_GDRIVE_DOC`), keeping the existing safety boundary.

Both paths are viable. The Local Bridge path is simpler but less structured. The Station Daemon path is more robust but requires the daemon to actually run on the local machine with its file bus synced.
