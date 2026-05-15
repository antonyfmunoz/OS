# Phase 93R.0 — Existing Local Daemon Discovery + Reconnection v1

**Date**: 2026-05-04
**Status**: COMPLETE
**Predecessor**: Phase 92 (Founder Approval Capture + Offer Lock v1)
**Test coverage**: N/A — discovery/documentation phase, no code changes
**Source code modified**: NO

---

## 1. Executive Summary

Phase 93R.0 discovered two complete, production-quality systems for VPS ↔ local workstation communication that were active as recently as 2026-05-02. The **Local Bridge** (services/) routes Discord messages to a local Claude Code session over Tailscale HTTP, with full reply-path back to Discord. The **Station Daemon** (eos_ai/substrate/) dispatches structured safe actions to the local workstation via a file-based bus with heartbeats and an MVP safety allow-list. Both systems are code-complete with documentation. Neither needs to be rebuilt. The gap is 2 missing capabilities (AI chat export parsing, local file inventory) and 4 partial capabilities that need wiring rather than building. One critical unknown remains: whether `forward_to_local()` is actually called in the discord_bot.py message handling path (no grep hits found).

---

## 2. Whether an Existing Daemon Was Found

**YES** — two distinct daemon/worker systems were found.

### System A: Local Bridge (Message Routing)

| Property | Value |
|----------|-------|
| Type | HTTP client/server pair |
| VPS side | `services/local_bridge_client.py` (134 lines) |
| Local side | `services/local_bridge_server.py` (243 lines) |
| Reply path | `services/local_bridge_send_to_discord.sh` (103 lines) + `services/cc_webhook_receiver.py` (240 lines) |
| Documentation | `services/LOCAL_BRIDGE_SETUP.md` (162 lines) |
| Transport | HTTP over Tailscale (VPS 100.77.233.50 ↔ Local 100.74.199.102) |
| Purpose | Route Discord messages to local CC sessions; route CC replies back to Discord |
| Status | Code-complete, env vars enabled (`EOS_LOCAL_BRIDGE_ENABLED=1`), NEEDS_LOCAL_VERIFICATION for running state |

### System B: Station Daemon (Substrate Actions)

| Property | Value |
|----------|-------|
| Type | Polling daemon with handler table |
| Implementation | `eos_ai/substrate/station_daemon.py` (859 lines) |
| Transport | `eos_ai/substrate/station_bus.py` (file bus) + `eos_ai/substrate/node_transport.py` (HTTP additive) |
| Contract | `eos_ai/substrate/station.py` (StationContract, ControlMode, StationHeartbeat, StationEvent) |
| Activation | `eos_ai/substrate/local_listener.py` (bounded triggers) |
| Bus files | `eos_ai/.substrate_station/antony-workstation.{inbox,outbox}.json` (both empty) |
| Logs | `logs/workstation.jsonl` (177KB, last entry 2026-05-02 22:35) |
| Purpose | Execute safe actions on local workstation (play sound, speak text, open URL, launch app, open scene, focus app) |
| Status | Code-complete, STALE_RISK (heartbeat stale events in log, file sync unknown) |

---

## 3. Whether It Appears Usable

### System A (Local Bridge): YES — highly usable

- Architecture is clean, well-documented, and purpose-built for this use case
- Health-check-first pattern means graceful degradation when local is offline
- Reply path (local → VPS → Discord) is complete
- The only concern is whether `discord_bot.py` actually calls `forward_to_local()` — no grep hits found. This must be investigated.

### System B (Station Daemon): YES — usable with extension

- Handler table pattern is designed for extension (adding new ActionKind + handler is a deliberate, reviewable change)
- Safety model is robust (explicit allow-list, dry-run, bounded vocabulary)
- File bus syncing between VPS and local is unknown — may need HTTP transport or file sync mechanism
- 5 of 11 needed capabilities are already PRESENT; 4 are PARTIAL (need wiring); only 2 are MISSING

---

## 4. What Files/Scripts Are Relevant

### Critical (must understand before any reconnection work)

| File | Lines | Role |
|------|-------|------|
| `services/local_bridge_client.py` | 134 | VPS → local message forwarding |
| `services/local_bridge_server.py` | 243 | Local message receiver + tmux injection |
| `services/local_bridge_send_to_discord.sh` | 103 | Local → VPS reply hook |
| `services/cc_webhook_receiver.py` | 240 | VPS reply endpoint |
| `services/LOCAL_BRIDGE_SETUP.md` | 162 | Full setup guide |
| `eos_ai/substrate/station_daemon.py` | 859 | Substrate daemon |
| `eos_ai/substrate/station.py` | ~160 | Contract + protocol |
| `eos_ai/substrate/station_bus.py` | 188 | File-based transport |

### Supporting (context for extension)

| File | Lines | Role |
|------|-------|------|
| `eos_ai/substrate/node_transport.py` | ~280 | HTTP transport adapter |
| `eos_ai/substrate/local_listener.py` | 397 | Bounded activation triggers |
| `eos_ai/substrate/control_bridge.py` | ~150 | Command queue per node |
| `eos_ai/substrate/task_queue.py` | ~230 | Priority queue with approval_waiting |
| `eos_ai/substrate/execution_worker.py` | ~400 | Event-driven execution bridge |
| `eos_ai/substrate/session_watcher.py` | ~330 | CC session state monitoring |
| `eos_ai/substrate/session_discord_bridge.py` | ~var | Discord UI for session events |
| `eos_ai/substrate/claude_session_bridge.py` | ~41K | Full CC session bridge |
| `eos_ai/gws_scanner.py` | ~var | Google Workspace document scanner |
| `eos_ai/gws_connector.py` | ~var | Google Workspace API connector |

---

## 5. What Must Be Checked from Local PC

| # | Check | Command | Why | Priority |
|---|-------|---------|-----|----------|
| 1 | Tailscale connected | `tailscale status` | All communication depends on this | CRITICAL |
| 2 | Bridge server running | `curl http://localhost:8766/health` | VPS → local routing | CRITICAL |
| 3 | Tmux sessions exist | `tmux list-sessions` | Message injection target | HIGH |
| 4 | CC Stop hook installed | `cat ~/.claude/settings.json` | Reply path | HIGH |
| 5 | send-to-discord.sh exists | `ls -la ~/.claude/hooks/send-to-discord.sh` | Reply hook | HIGH |
| 6 | VPS reachable | `curl http://100.77.233.50:8765/health` | Reply endpoint | HIGH |
| 7 | Bridge server version | Compare with VPS copy | File currency | MEDIUM |
| 8 | Station daemon running | `ps aux \| grep station_daemon` | Substrate actions | MEDIUM |
| 9 | WSL aiohttp installed | `pip show aiohttp` | Bridge dependency | MEDIUM |
| 10 | Inbox directory | `ls ~/eos_inbox/` | Fallback storage | LOW |

---

## 6. Whether Phase 93R Should Reuse, Repair, or Replace

### Recommendation: REUSE + EXTEND

**Do NOT replace.** Both systems are code-complete, well-documented, and architecturally sound. The Local Bridge (System A) is the more immediately useful system — it already routes messages bidirectionally and the local server is built for extension.

**Do NOT repair.** There's no evidence of breakage — only stale state from the daemon not running. Reconnection is a startup task, not a repair task.

**EXTEND** for the ingestion use case:

1. Verify local bridge is running and end-to-end path works
2. Investigate the `forward_to_local()` integration gap in discord_bot.py
3. Add 2-3 new endpoints to `local_bridge_server.py` for structured work orders
4. Add result writeback endpoint to VPS side
5. Build AI chat export parser (new module)
6. Build local file inventory capability (new ActionKind or simple script)

---

## 7. Recommended Next Phase

### Phase 93R.1 — Bind Existing Local Bridge to Work Order Contract

**Rationale**: The Local Bridge (System A) is the more immediately actionable system. It's HTTP-based, health-check-gated, and already bidirectional. The Station Daemon (System B) is more robust but requires resolving the file bus sync question.

**Phase 93R.1 should:**
1. Verify local bridge end-to-end (founder runs checks from §5)
2. Investigate and resolve the `forward_to_local()` integration gap
3. Define a work order JSON schema (compatible with ControlCommand envelope)
4. Add `/work-order` endpoint to `local_bridge_server.py`
5. Add `/work-order-result` endpoint to VPS webhook receiver
6. Define approval gate using existing cc-prompt + Discord buttons pattern
7. Implement first work order type: local file inventory
8. Test round-trip: VPS dispatches work order → local executes → result returns to VPS

**Why not jump to ingestion?**
The transport must be verified and the work order contract must be defined before any real ingestion work orders can flow. Phase 93R.1 proves the bridge works. Phase 93R.2 uses it for actual ingestion.

**After Phase 93R.1:**
- Phase 93R.2 — First Ingestion Work Order Execution (local file inventory + AI chat export)
- Phase 93R.3 — Google Workspace Document Ingestion (via VPS-side GWS tools, no local bridge needed)

---

## 8. What Changed

| Before Phase 93R.0 | After Phase 93R.0 |
|--------------------|-------------------|
| Assumed no existing daemon | Discovered 2 complete systems |
| No inventory of VPS ↔ local infrastructure | 18 relevant files documented with status |
| Unknown communication model | HTTP over Tailscale confirmed, file bus documented |
| Unknown capability gaps | 5 PRESENT, 4 PARTIAL, 2 MISSING out of 11 needed |
| No reconnection plan | 10-step local verification checklist + safe reconnection sequence |
| Unclear next phase | Clear recommendation: reuse + extend, not replace |

---

## 9. Safety Attestation

| Question | Answer |
|----------|--------|
| Did this phase scrape? | NO |
| Did this phase use computer control? | NO |
| Did this phase call APIs? | NO |
| Did this phase send or post anything? | NO |
| Did this phase execute payments? | NO |
| Did this phase promote memory? | NO |
| Did this phase mutate source code? | NO |
| Did this phase start/stop any daemon? | NO |
| Did this phase edit/delete/move user files? | NO |
| Did this phase capture credentials? | NO |
| Was governance bypassed? | NO |
