# Bridge Healthcheck — Local PC Checklist v1

**Date**: 2026-05-04
**Phase**: 94R — Existing Local Bridge Healthcheck + Work Order Dispatch Readiness v1
**Purpose**: Exact checklist for the founder to run on the local Windows/WSL PC before Work Order 001 can be dispatched.

---

## Instructions

Run each check from the local Windows WSL terminal (or Termius SSH into local WSL).
Mark PASS / FAIL for each. Commands come from existing documentation (`LOCAL_BRIDGE_SETUP.md`, `local_worker_healthcheck_checklist_v1.md`).
Where no verified command exists, the check is marked NEEDS_LOCAL_VERIFICATION with instructions on what to look for.

All CRITICAL checks must PASS before dispatch.

---

## Check 1 — Tailscale Connected

| Field | Value |
|-------|-------|
| **Priority** | CRITICAL |
| **Command** | `tailscale status` |
| **Expected** | Shows VPS peer `100.77.233.50` as connected/active |
| **If FAIL** | Run `sudo tailscale up` |
| **Source** | `LOCAL_BRIDGE_SETUP.md` Troubleshooting: "Tailscale unreachable" |

---

## Check 2 — VPS Reachable from Local

| Field | Value |
|-------|-------|
| **Priority** | CRITICAL |
| **Command** | `tailscale ping 100.77.233.50` |
| **Expected** | Reply within 1-2 seconds |
| **If FAIL** | Check Tailscale status, check VPS is up |
| **Source** | `local_worker_healthcheck_checklist_v1.md` Check 2 |

---

## Check 3 — Local Bridge Server Running

| Field | Value |
|-------|-------|
| **Priority** | CRITICAL |
| **Command** | `curl -s http://localhost:8766/health` |
| **Expected** | `{"status": "ok", "machine": "local"}` |
| **If FAIL** | Start bridge: `tmux new-session -d -s bridge "python3 ~/local_bridge_server.py"` |
| **Source** | `LOCAL_BRIDGE_SETUP.md` §3 + §6 |

---

## Check 4 — Bridge Reachable from VPS

| Field | Value |
|-------|-------|
| **Priority** | CRITICAL |
| **Command** | From VPS: `curl -s http://100.74.199.102:8766/health` |
| **Expected** | `{"status": "ok", "machine": "local"}` |
| **If FAIL** | Verify Checks 1-3 all pass first |
| **Source** | `LOCAL_BRIDGE_SETUP.md` §6 |

---

## Check 5 — Tmux Sessions Exist

| Field | Value |
|-------|-------|
| **Priority** | HIGH |
| **Command** | `tmux list-sessions` |
| **Expected** | Shows at least one session (e.g., `dex_builder_main`, `bridge`) |
| **If FAIL** | Create session: `tmux new-session -d -s dex_builder_main` then `tmux send-keys -t dex_builder_main "claude" Enter` |
| **Source** | `LOCAL_BRIDGE_SETUP.md` §4 |

---

## Check 6 — Station Daemon Running (if required)

| Field | Value |
|-------|-------|
| **Priority** | LOW — not required for HTTP bridge path |
| **Command** | `ps aux \| grep station_daemon` |
| **Expected** | Process found, or not running (acceptable — HTTP bridge does not require daemon) |
| **If not running** | Not a blocker. Work orders use HTTP bridge, not file bus. |
| **Source** | `phase93r0_existing_local_daemon_discovery_report.md` §6 — HTTP bridge is primary path |

---

## Check 7 — Local Repo or /opt/OS Sync Exists

| Field | Value |
|-------|-------|
| **Priority** | MEDIUM |
| **Check** | Does the local machine have a copy of `local_bridge_server.py`? |
| **Command** | `ls -la ~/local_bridge_server.py` |
| **Expected** | File exists |
| **If FAIL** | Copy from VPS: `scp root@100.77.233.50:/opt/OS/services/local_bridge_server.py ~/local_bridge_server.py` |
| **Source** | `LOCAL_BRIDGE_SETUP.md` §1 |

---

## Check 8 — Local Worker Can Read Work Orders

| Field | Value |
|-------|-------|
| **Priority** | HIGH |
| **Check** | Can the work order inbox directory be created and read? |
| **Command** | `mkdir -p ~/eos_work_orders && ls -la ~/eos_work_orders/` |
| **Expected** | Directory exists (empty is fine) |
| **If FAIL** | The `mkdir -p` command creates it — should not fail |
| **Source** | `existing_bridge_binding_plan_v1.md` §4 — local inbox at `~/eos_work_orders/` |

---

## Check 9 — Local Worker Can Write Results

| Field | Value |
|-------|-------|
| **Priority** | HIGH |
| **Check** | Can the local worker write result files? |
| **Command** | `touch ~/eos_work_orders/test_write.tmp && rm ~/eos_work_orders/test_write.tmp && echo "WRITE OK"` |
| **Expected** | Prints `WRITE OK` |
| **If FAIL** | Check filesystem permissions on `~/eos_work_orders/` |
| **Source** | `existing_bridge_binding_plan_v1.md` §5 — results written to `~/eos_work_orders/{id}_result.json` |

---

## Check 10 — Browser Session Available

| Field | Value |
|-------|-------|
| **Priority** | HIGH (for Google Workspace work orders) |
| **Check** | Is a browser available on the local machine? |
| **Command** | NEEDS_LOCAL_VERIFICATION — open browser from desktop or check `which google-chrome` or `which firefox` |
| **Expected** | Browser launches or binary found |
| **If FAIL** | Install or verify browser access from WSL (may need `cmd.exe /c start chrome` for Windows) |
| **Source** | `local_worker_healthcheck_checklist_v1.md` Check 10 |

---

## Check 11 — Google Account Logged In

| Field | Value |
|-------|-------|
| **Priority** | HIGH (for Google Workspace work orders) |
| **Check** | Is the founder's Google account logged in in the browser? |
| **Command** | NEEDS_LOCAL_VERIFICATION — open browser → navigate to `https://drive.google.com` → verify account is logged in |
| **Expected** | Google Drive loads with founder's account |
| **If FAIL** | Log into Google account in browser |
| **Source** | `local_worker_healthcheck_checklist_v1.md` Check 10, `work_order_001` — source targets are Google Drive folders |

---

## Check 12 — No Credentials or Tokens Displayed

| Field | Value |
|-------|-------|
| **Priority** | MEDIUM |
| **Check** | Are any credentials exposed in environment that could leak into work order results? |
| **Command** | `env \| grep -iE '(api_key\|secret\|token\|password)' \| wc -l` |
| **Expected** | Review output — ensure no secrets will be included in work order payloads or results |
| **If concern** | This is informational. Work order contract forbids credential capture. |
| **Source** | `local_worker_healthcheck_checklist_v1.md` Check 14 |

---

## Check 13 — No Outbound Actions During Healthcheck

| Field | Value |
|-------|-------|
| **Priority** | CRITICAL |
| **Check** | This healthcheck itself must not send emails, post content, or perform any outbound action |
| **Command** | N/A — attestation |
| **Expected** | Founder confirms: running these checks did not trigger any outbound communication |
| **If concern** | Stop immediately and report |
| **Source** | Phase 94R safety constraints |

---

## Check 14 — VPS Webhook Reachable from Local

| Field | Value |
|-------|-------|
| **Priority** | HIGH |
| **Command** | `curl -s http://100.77.233.50:8765/health` |
| **Expected** | HTTP 200 response |
| **If FAIL** | VPS webhook receiver may be down — check `docker ps` on VPS for `os-discord` container |
| **Source** | `LOCAL_BRIDGE_SETUP.md` §6, `local_worker_healthcheck_checklist_v1.md` Check 9 |

---

## Check 15 — CC Stop Hook Installed

| Field | Value |
|-------|-------|
| **Priority** | HIGH |
| **Command** | `cat ~/.claude/settings.json \| grep -A2 Stop` |
| **Expected** | Stop hook pointing to `send-to-discord.sh` |
| **If FAIL** | See `LOCAL_BRIDGE_SETUP.md` §5 for hook installation |
| **Source** | `LOCAL_BRIDGE_SETUP.md` §5 |

---

## Check 16 — send-to-discord.sh Exists

| Field | Value |
|-------|-------|
| **Priority** | HIGH |
| **Command** | `ls -la ~/.claude/hooks/send-to-discord.sh` |
| **Expected** | File exists with execute permission |
| **If FAIL** | `scp root@100.77.233.50:/opt/OS/services/local_bridge_send_to_discord.sh ~/.claude/hooks/send-to-discord.sh && chmod +x ~/.claude/hooks/send-to-discord.sh` |
| **Source** | `LOCAL_BRIDGE_SETUP.md` §5 |

---

## Check 17 — aiohttp Installed

| Field | Value |
|-------|-------|
| **Priority** | MEDIUM |
| **Command** | `pip show aiohttp` |
| **Expected** | Package info displayed |
| **If FAIL** | `pip install aiohttp` |
| **Source** | `LOCAL_BRIDGE_SETUP.md` §2 |

---

## Summary Table

| # | Check | Priority | Status |
|---|-------|----------|--------|
| 1 | Tailscale connected | CRITICAL | ☐ |
| 2 | VPS reachable from local | CRITICAL | ☐ |
| 3 | Local bridge server running | CRITICAL | ☐ |
| 4 | Bridge reachable from VPS | CRITICAL | ☐ |
| 5 | Tmux sessions exist | HIGH | ☐ |
| 6 | Station daemon running | LOW | ☐ (not required) |
| 7 | Local repo / file sync | MEDIUM | ☐ |
| 8 | Work order inbox readable | HIGH | ☐ |
| 9 | Results writable | HIGH | ☐ |
| 10 | Browser available | HIGH | ☐ |
| 11 | Google account logged in | HIGH | ☐ |
| 12 | No credentials displayed | MEDIUM | ☐ |
| 13 | No outbound during healthcheck | CRITICAL | ☐ |
| 14 | VPS webhook reachable | HIGH | ☐ |
| 15 | CC Stop hook installed | HIGH | ☐ |
| 16 | send-to-discord.sh exists | HIGH | ☐ |
| 17 | aiohttp installed | MEDIUM | ☐ |

**Gate**: All 5 CRITICAL checks must PASS.
At least 7 of 9 HIGH checks should PASS (Checks 10-11 only required for Google Workspace work orders).
MEDIUM/LOW checks are recommended but not blocking.

---

## After All Checks Pass

1. Report results to VPS session
2. Confirm: `curl -s http://100.74.199.102:8766/health` from VPS returns `{"status": "ok", "machine": "local"}`
3. VPS will dispatch Work Order 001 in Phase 94L
