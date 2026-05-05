# Local Worker Healthcheck Checklist v1

**Date**: 2026-05-04
**Phase**: 93R.1 — Bind Existing Local Bridge to Work Order Contract v1
**Purpose**: Founder-executable checklist to verify local PC is ready to receive and execute work orders.

---

## Instructions

Run each check from the local Windows WSL terminal (or Termius SSH into local WSL).
Mark PASS / FAIL / SKIP for each. All CRITICAL checks must PASS before any work order can be dispatched.

---

## Check 1 — Tailscale Connected

| Field | Value |
|-------|-------|
| **Priority** | CRITICAL |
| **Command** | `tailscale status` |
| **Expected** | Shows VPS peer `100.77.233.50` as connected/active |
| **If FAIL** | Run `sudo tailscale up` — if already up, check network connectivity |
| **Why** | All VPS ↔ local communication flows through Tailscale private network |

---

## Check 2 — VPS Reachable from Local

| Field | Value |
|-------|-------|
| **Priority** | CRITICAL |
| **Command** | `tailscale ping 100.77.233.50` |
| **Expected** | Reply within 1-2 seconds |
| **If FAIL** | Tailscale may be connected but VPS is down — check VPS status |
| **Why** | Result writeback and approval gates require VPS reachability |

---

## Check 3 — Local Bridge Server Running

| Field | Value |
|-------|-------|
| **Priority** | CRITICAL |
| **Command** | `curl -s http://localhost:8766/health` |
| **Expected** | `{"status": "ok", "machine": "local"}` |
| **If FAIL** | Start bridge server: `tmux new-session -d -s bridge "python3 ~/local_bridge_server.py"` |
| **Why** | Work orders are dispatched via HTTP POST to this server |

---

## Check 4 — Bridge Server Reachable from VPS

| Field | Value |
|-------|-------|
| **Priority** | CRITICAL |
| **Command** | From VPS: `curl -s http://100.74.199.102:8766/health` |
| **Expected** | `{"status": "ok", "machine": "local"}` |
| **If FAIL** | Check Tailscale connectivity (Check 1) and bridge server (Check 3) |
| **Why** | VPS dispatches work orders to this address — must be reachable |

---

## Check 5 — Tmux Sessions Exist

| Field | Value |
|-------|-------|
| **Priority** | HIGH |
| **Command** | `tmux list-sessions` |
| **Expected** | Shows at least one session (e.g., `dex_builder_main`, `dex_product_main`) |
| **If FAIL** | Create session: `tmux new-session -d -s dex_builder_main` then start Claude Code inside it |
| **Why** | Message injection and CC session control require tmux sessions |

---

## Check 6 — Claude Code or Cursor Available

| Field | Value |
|-------|-------|
| **Priority** | HIGH |
| **Command** | `which claude` or check Cursor is installed |
| **Expected** | Claude Code binary found, or Cursor installed and launchable |
| **If FAIL** | Install Claude Code CLI or verify Cursor installation |
| **Why** | Local AI worker needs an execution environment for work orders |

---

## Check 7 — CC Stop Hook Installed

| Field | Value |
|-------|-------|
| **Priority** | HIGH |
| **Command** | `cat ~/.claude/settings.json \| grep -A2 Stop` |
| **Expected** | Stop hook pointing to `send-to-discord.sh` |
| **If FAIL** | Copy hook config from VPS: see `services/LOCAL_BRIDGE_SETUP.md` §Hook Setup |
| **Why** | Reply path (local CC → VPS → Discord) depends on the Stop hook |

---

## Check 8 — send-to-discord.sh Exists and Executable

| Field | Value |
|-------|-------|
| **Priority** | HIGH |
| **Command** | `ls -la ~/.claude/hooks/send-to-discord.sh` |
| **Expected** | File exists with execute permission (`-rwxr-xr-x`) |
| **If FAIL** | Copy from VPS: `scp root@100.77.233.50:/opt/OS/services/local_bridge_send_to_discord.sh ~/.claude/hooks/send-to-discord.sh && chmod +x ~/.claude/hooks/send-to-discord.sh` |
| **Why** | This script is the CC Stop hook that sends replies back to Discord |

---

## Check 9 — VPS Webhook Reachable from Local

| Field | Value |
|-------|-------|
| **Priority** | HIGH |
| **Command** | `curl -s http://100.77.233.50:8765/health` |
| **Expected** | HTTP 200 response |
| **If FAIL** | VPS webhook receiver may be down — check `docker ps` on VPS for `os-discord` container |
| **Why** | Result writeback and approval POSTs go to this endpoint |

---

## Check 10 — Browser with Google Login

| Field | Value |
|-------|-------|
| **Priority** | HIGH (for Google Workspace work orders) |
| **Command** | Open browser → navigate to `https://drive.google.com` |
| **Expected** | Google Drive loads with founder's account logged in |
| **If FAIL** | Log into Google account in the browser |
| **Why** | Google Workspace work orders require browser-based navigation with active Google session |

---

## Check 11 — Work Order Inbox Directory

| Field | Value |
|-------|-------|
| **Priority** | MEDIUM |
| **Command** | `mkdir -p ~/eos_work_orders && ls -la ~/eos_work_orders/` |
| **Expected** | Directory exists (empty is fine) |
| **If FAIL** | The `mkdir -p` command creates it — should not fail |
| **Why** | Local bridge server will write received work orders to this directory |

---

## Check 12 — aiohttp Installed

| Field | Value |
|-------|-------|
| **Priority** | MEDIUM |
| **Command** | `pip show aiohttp` |
| **Expected** | Package info displayed (version, location) |
| **If FAIL** | `pip install aiohttp` |
| **Why** | Bridge server (`local_bridge_server.py`) requires aiohttp |

---

## Check 13 — Local Bridge Server Version Current

| Field | Value |
|-------|-------|
| **Priority** | MEDIUM |
| **Command** | `md5sum ~/local_bridge_server.py` and compare with VPS: `md5sum /opt/OS/services/local_bridge_server.py` |
| **Expected** | Hashes match |
| **If FAIL** | Copy fresh version: `scp root@100.77.233.50:/opt/OS/services/local_bridge_server.py ~/local_bridge_server.py` then restart bridge |
| **Why** | Outdated server may lack endpoints or fixes |

---

## Check 14 — No Secrets in Environment

| Field | Value |
|-------|-------|
| **Priority** | MEDIUM |
| **Command** | `env \| grep -iE '(api_key\|secret\|token\|password)' \| wc -l` |
| **Expected** | Review output — ensure no secrets will be transmitted in work order results |
| **If FAIL** | This is informational — no action needed unless secrets appear in work order payloads |
| **Why** | Work order contract forbids credential capture. This check is awareness, not a gate. |

---

## Summary Table

| # | Check | Priority | Status |
|---|-------|----------|--------|
| 1 | Tailscale connected | CRITICAL | ☐ |
| 2 | VPS reachable from local | CRITICAL | ☐ |
| 3 | Local bridge server running | CRITICAL | ☐ |
| 4 | Bridge reachable from VPS | CRITICAL | ☐ |
| 5 | Tmux sessions exist | HIGH | ☐ |
| 6 | Claude Code or Cursor available | HIGH | ☐ |
| 7 | CC Stop hook installed | HIGH | ☐ |
| 8 | send-to-discord.sh exists | HIGH | ☐ |
| 9 | VPS webhook reachable | HIGH | ☐ |
| 10 | Browser with Google login | HIGH | ☐ |
| 11 | Work order inbox directory | MEDIUM | ☐ |
| 12 | aiohttp installed | MEDIUM | ☐ |
| 13 | Bridge server version current | MEDIUM | ☐ |
| 14 | No secrets in environment | MEDIUM | ☐ |

**Gate**: All 4 CRITICAL checks must PASS before dispatching any work order.
All HIGH checks should PASS before dispatching Google Workspace work orders.
MEDIUM checks are recommended but not blocking.

---

## After All Checks Pass

1. Notify VPS: founder can run `curl -s http://100.74.199.102:8766/health` from VPS to confirm
2. Mark this checklist as COMPLETE with date
3. Proceed to Phase 94L — first work order dispatch

**Phase 93R.1 defines what to check. Phase 94L uses this checklist before first dispatch.**
