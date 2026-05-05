# W0-001 Test Status v1

**Phase**: 94D.5 — Relay Wiring + GUI Healthcheck + W0-001 Relaunch
**Date**: 2026-05-04
**Last Updated**: 2026-05-04

---

## Transport Health (confirmed 2026-05-04)

| Check | Status | Detail |
|-------|--------|--------|
| SSH to local | HEALTHY | `SSH_OK` returned |
| Bridge health | HEALTHY | `{"status": "ok", "machine": "local"}` |
| Bridge tmux sessions | ACTIVE | `[bridge, umh_core]` |
| Local inbox dir | EXISTS | `~/eos_inbox/` (has umh_core.txt from prior dispatch) |
| Local outbox dir | EXISTS | `~/eos_outbox/` (empty, ready) |
| Local advisor messages dir | EXISTS | `~/eos_advisor_messages/` (empty, ready) |
| VPS station dir | EXISTS | `/opt/OS/eos_ai/.substrate_station/` |

## Code Status

| Module | Status | Tests |
|--------|--------|-------|
| `advisor_bridge_transport.py` | COMPILED | 16/16 passing |
| `local_worker_relay_packets.py` | COMPILED | 16/16 passing |
| `gui_backend_healthcheck.py` | COMPILED | 9/9 passing |

## W0-001 Relay Packet Status

| Field | Value |
|-------|-------|
| Worker mode | AUTO |
| Approval routing | advisor_relay |
| Local manual approval | DISABLED |
| Playwright | DISABLED |
| Preferred backend | GUI_COMPUTER_USE |
| GUI healthcheck required | YES |
| Target account | antonyfm@empyreanstudios.co |
| Source class | Google Drive / Google Docs |
| Blocked actions | 15 (all governance-blocked) |
| Blocked targets | gmail, account_switching, google_calendar, google_contacts, google_photos, youtube |
| Validation errors | 0 |

## Dispatch Status

Corrected relay packet dispatched to local via bridge: **YES**

## Local Worker Claim Status

Local worker automated claim: **NOT YET** (requires local worker daemon)

## First Approval Request Status

First approval request reached VPS: **PENDING** (requires local worker to process packet)

## Next Action

**START_LOCAL_WORKER** — The relay packet has been dispatched. The local
`umh_core` tmux session has the packet in its inbox. A local worker
daemon or manual processing of the packet would produce the first
approval request in `~/eos_outbox/`.

## No Unsafe Actions Performed

- No computer use: YES
- No Google Drive opened: YES
- No Playwright used: YES
- No Gmail opened: YES
- No accounts switched: YES
- No files sent/posted/edited/deleted/moved: YES
- No permissions changed: YES
- No credentials captured: YES
- No memory promoted: YES
- Governance bypassed: NO
