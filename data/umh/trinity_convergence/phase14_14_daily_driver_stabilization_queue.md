# Daily Driver Stabilization Queue

Source: Phase 14.14A daily-driver acceptance trial + Phase 14.14C grounding analysis.
Updated: 2026-06-09

## Status Key

- **pending** — identified, not yet fixed
- **fixed** — code change applied
- **verified** — fix confirmed live

---

## Failures

### F1 — "What should I do next" lacks system awareness

| Field | Value |
|---|---|
| failure_id | F1 |
| surface | dex_chat |
| user_action | "What should I do next?" |
| expected | Response references real tickets, work packets, organism state |
| actual | Generic advice with no system awareness |
| root_cause | LLM generates response without injecting organism/ticket/mesh state |
| severity | medium |
| blocked_daily_driver | false |
| fix_status | pending |
| recommended_fix | Inject system_status grounding data into conversation prompt for planning queries |

### F2 — Status queries hallucinate system state

| Field | Value |
|---|---|
| failure_id | F2 |
| surface | dex_chat |
| user_action | "How are things?" / "What's the current status?" |
| expected | Real data from Docker, providers, work packets |
| actual | LLM invents system state from training data |
| root_cause | Status-seeking detection missing for some phrasings; conversation path reached LLM without data |
| severity | critical |
| blocked_daily_driver | true |
| fix_status | fixed |
| fix_details | Phase 14.14C: grounding firewall with detect_status_seeking(), _route_grounded_query(), 70+ patterns, 13 collectors |

### F3 — Work packet creation returns trace ID not packet

| Field | Value |
|---|---|
| failure_id | F3 |
| surface | work_packet |
| user_action | "Create a work packet for X" |
| expected | Packet created with ID and summary shown |
| actual | Returns trace ID string, no packet metadata |
| root_cause | Handler response formatting — returns execution trace, not structured packet response |
| severity | medium |
| blocked_daily_driver | false |
| fix_status | pending |
| recommended_fix | Format work packet creation response with packet ID, title, status |

### F4 — Blocker query returns trace ID not blocker list

| Field | Value |
|---|---|
| failure_id | F4 |
| surface | dex_chat |
| user_action | "What is blocked?" |
| expected | List of blocked work packets with reasons |
| actual | Returns trace ID |
| root_cause | Handler dispatched to advisor.handle_signal() instead of deterministic blocker reader |
| severity | high |
| blocked_daily_driver | true |
| fix_status | fixed |
| fix_details | Phase 14.14C: handle_grounded_blocked() and handle_grounded_composite_blockers() read real work_packets.jsonl |

### F5 — Reports fabricate session data

| Field | Value |
|---|---|
| failure_id | F5 |
| surface | report |
| user_action | "What reports were created today?" |
| expected | List from reports.jsonl with timestamps |
| actual | LLM invents report names and dates |
| root_cause | Report query fell through to LLM without real report file data |
| severity | high |
| blocked_daily_driver | true |
| fix_status | fixed |
| fix_details | Phase 14.14C: handle_grounded_reports() reads reports.jsonl; status-seeking pattern "reports today" → recent_reports |

### F6 — Work packet loop untestable (blocked by F3)

| Field | Value |
|---|---|
| failure_id | F6 |
| surface | work_packet |
| user_action | Full work packet lifecycle (create → decompose → assign → complete) |
| expected | End-to-end lifecycle works |
| actual | Cannot test — F3 blocks creation step |
| root_cause | Depends on F3 fix |
| severity | medium |
| blocked_daily_driver | false |
| fix_status | pending |

### F7 — CC session launcher missing

| Field | Value |
|---|---|
| failure_id | F7 |
| surface | dex_chat |
| user_action | "Send this to Claude Code" |
| expected | Starts a Claude Code session with the given task |
| actual | No mechanism to launch CC sessions from cockpit |
| root_cause | CC_SEND intent handler exists but no session launcher wired |
| severity | low |
| blocked_daily_driver | false |
| fix_status | pending |

### F8 — "Restart services" goes to LLM

| Field | Value |
|---|---|
| failure_id | F8 |
| surface | vps |
| user_action | "Restart services" |
| expected | Routes to VPS catalog restart action |
| actual | Falls through to generic LLM conversation |
| root_cause | "restart services" not in _VPS_CONTROL_SIGNALS |
| severity | high |
| blocked_daily_driver | true |
| fix_status | fixed |
| fix_details | Phase 14.14C: added "restart services", "restart all services" to _VPS_CONTROL_SIGNALS and _VPS_KEYWORD_MAP |

---

## Priority Order (remaining)

1. F3 — Work packet creation response formatting
2. F6 — Work packet lifecycle (depends on F3)
3. F1 — System-aware "what next" planning
4. F7 — CC session launcher

## Resolved This Phase

- F2 — Status hallucination (grounding firewall)
- F4 — Blocker query (grounded handlers)
- F5 — Report fabrication (grounded reports)
- F8 — Restart services routing (VPS signals + catalog)
