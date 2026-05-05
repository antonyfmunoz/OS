# Current Topology Transport Binding v1

**Phase**: 94D.5 — Relay Wiring + GUI Healthcheck + W0-001 Relaunch
**Status**: CONFIRMED
**Date**: 2026-05-04

---

## 1. Current Topology Profile

```
topology_id: founder_current
owner_id: antonyfm

Node 1: VPS Orchestrator
  node_id: vps_orchestrator
  type: cloud_vps
  roles: orchestrator, control_plane, reporting_node
  capabilities: llm_inference, orchestration, scheduling, api_access, file_storage, docker
  hostname: srv1500858
  os: linux
  ip: 100.77.233.50 (Tailscale)
  online: YES (confirmed 2026-05-04)

Node 2: Local PC Worker
  node_id: local_pc_worker
  type: local_workstation
  roles: worker, computer_use_worker, browser_session_node, local_file_node
  capabilities: gui_computer_use, browser_session, local_files, screen_control, audio
  hostname: desktop-lvguiq9
  os: windows_wsl
  ip: 100.74.199.102 (Tailscale)
  online: YES (confirmed 2026-05-04)
```

## 2. Confirmed VPS → Local Path

| Transport | Endpoint | Status | Latency |
|-----------|----------|--------|---------|
| HTTP Bridge | `POST http://100.74.199.102:8766/message` | HEALTHY | <100ms |
| SSH | `ssh -i ~/.ssh/id_ed25519 ... 'DESKTOP-LVGUIQ9\antonys beast pc'@100.74.199.102` | HEALTHY | <1s |
| File inbox | `~/eos_inbox/{session_name}.txt` via bridge | WORKING | bridge-speed |
| Station bus | `/opt/OS/eos_ai/.substrate_station/` (VPS-local only) | AVAILABLE | local |

**Primary**: HTTP bridge `forward_to_local(text, session_name)` → bridge server → tmux inject or file inbox.

**Fallback**: SSH → wsl → tmux send-keys or file write.

## 3. Confirmed Local → VPS Path

| Transport | Endpoint | Status |
|-----------|----------|--------|
| HTTP POST | `POST http://100.77.233.50:8765/cc-reply` | AVAILABLE |
| File outbox | `~/eos_outbox/` (polled via SSH from VPS) | AVAILABLE |

**Primary for this test**: File-based outbox. Worker writes advisor messages to `~/eos_outbox/`, VPS polls via SSH.

**Reason**: The `/cc-reply` endpoint is wired for CC stop-hook replies to Discord, not for structured advisor messages. The file outbox is the safest relay path that doesn't modify existing bridge internals.

## 4. Current Local Inbox Path

`/home/antonys_beast_pc/eos_inbox/umh_core.txt`

Confirmed: file exists from prior W0-001 dispatch (7864 bytes, 2026-05-04 10:49).

## 5. Current Local Outbox Path

`/home/antonys_beast_pc/eos_outbox/`

Confirmed: directory exists, currently empty, ready for advisor message files.

## 6. Healthcheck Commands

```bash
# SSH health
ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=8 'DESKTOP-LVGUIQ9\antonys beast pc'@100.74.199.102 'echo SSH_OK'

# Bridge health
curl -s --connect-timeout 5 http://100.74.199.102:8766/health

# Bridge status (tmux sessions, inbox files)
curl -s --connect-timeout 5 http://100.74.199.102:8766/status
```

## 7. Restart Bridge Command

```bash
ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=8 'DESKTOP-LVGUIQ9\antonys beast pc'@100.74.199.102 'wsl -e bash -c "tmux kill-session -t bridge 2>/dev/null; tmux new-session -d -s bridge \"python3 ~/local_bridge_server.py\""'
```

## 8. Acknowledgement Method

Worker writes acknowledgement to `~/eos_outbox/ack_{work_order_id}.json`.
VPS polls via SSH: `ssh ... 'wsl -e bash -c "cat ~/eos_outbox/ack_*.json"'`

## 9. Gaps

| Gap | Severity | Workaround |
|-----|----------|------------|
| No real-time local→VPS push | LOW | File-based polling from VPS via SSH |
| `/cc-reply` not wired for advisor messages | LOW | Use file outbox instead |
| No `station_control.py` | LOW | Not needed for this phase |
| No auto-polling daemon on VPS | LOW | Manual polling for this test |

## 10. Chosen Minimal Relay Transport for This Test

```
VPS → Local:  HTTP bridge POST /message → file inbox (primary)
              SSH → wsl → file write (fallback)

Local → VPS:  Worker writes to ~/eos_outbox/*.json
              VPS reads via SSH → wsl → cat (polling)
```

This is a topology-specific transport binding. It is NOT the universal architecture. It works for the current two-node topology with Tailscale + SSH + HTTP bridge.

## Files

`eos_ai/substrate/advisor_bridge_transport.py`
