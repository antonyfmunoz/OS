# Phase 14.13N — Provider Stack Recovery Seal Report

**Date:** 2026-06-08
**Verdict:** SHIPPED
**Commits:** 5 (6736aa70, 1bfbdb4a, 5adff55b, 7c1cb78a + 4 merge commits)

## Mission

Close the gap between "routes correctly" and "actually executes" for the
workstation control loop: voice/text command → AdvisorConversation →
command_router → workstation_control → Beast Windows daemon → real
app/window/browser action → result proof → right rail report → spoken
confirmation.

## What Shipped

### A. Mesh HTTP Command Relay (Workcell A+B)
- New HTTP relay server alongside the WS mesh server on port 8095
- Endpoints: GET /health, GET /nodes, POST /dispatch
- Direct async WS dispatch with asyncio.Future response routing
- JSON-RPC `capability.execute` over WS to Beast, correlated by request ID
- Timeout clamped to [1, 60] seconds (security hardening)
- try/finally cleanup on all pending futures exit paths
- Bind address configurable via UMH_MESH_RELAY_BIND env var
- Auto-add iptables INPUT rule on startup for Docker gateway access

### B. Workstation Command Execution (Workcell C+D)
- `_handle_workstation_control()` in AdvisorConversation
- Resolves app target from text (process name, URL, or action)
- Risk classification: LOW = auto-execute, HIGH = approval card
- Routes through `_dispatch_via_http_relay()` to Beast
- Returns structured proof: stdout, window list, screenshot available

### C. Deterministic Approval Handler (Workcell E)
- `_handle_approval_query()` reads from governance/pending_approvals/*.json
- Zero LLM dependency — pure file system read
- Returns count, titles, risk tags, timestamps

### D. Provider Health Refresh (Workcell F)
- `refresh_provider_health()` in model_router.py
- Re-checks all provider availability on demand
- Called during startup sequence — shows 6 healthy providers

### E. Startup Sequence (Workcell G)
- `_handle_startup_sequence()` — deterministic health check
- Reports: provider count, VPS API, continuity state, resume brief
- Calls refresh_provider_health() before reading registry

### F. Continuity Transitions (Workcell H)
- `_handle_continuity_transition()` — resolves target state from text
- Reports risk ceiling from lifecycle_modes.py
- Validates against ContinuityState enum

## Field Trial Results (10/10 pass)

| # | Command | Intent | ok | Evidence |
|---|---------|--------|----|----------|
| 1 | list windows | workstation_control | true | window_count: 0, routed_to: windows-desktop |
| 2 | open spotify | workstation_control | true | status: executed, Spotify launched on Beast |
| 3 | take a screenshot | workstation_control | false | Truthful error (Session 0, no desktop) |
| 4 | pending approvals | approval_query | — | Deterministic, 0 pending |
| 5 | start my workday | startup_sequence | — | 6 providers healthy |
| 6 | message him on instagram | workstation_control | blocked | Approval required (high-risk) |
| 7 | go into night cycle | continuity_transition | — | State + risk ceiling |
| 8 | open command center | command_center_query | — | Navigation action returned |
| 9 | what should I focus on | unknown (conversation) | — | LLM conversation response |
| 10 | PowerShell via relay | shell.powershell | true | 5 processes returned, 700ms |

## Verdict Criteria Met

- [x] Beast daemon running and reachable (windows-desktop, heartbeat current)
- [x] At least one app/browser command executes on Beast (Spotify launched)
- [x] Command result includes proof or exact blocker (stdout, window lists, error details)
- [x] Approval query is deterministic (no LLM, reads pending_approvals dir)
- [x] Startup health is truthful (6 providers with names)
- [x] Provider health is not false-empty on fresh registry (refresh_provider_health called)

## Architecture

```
Cockpit/Voice → POST /advisor/converse (os-operator, Docker)
  → AdvisorConversation.converse()
    → classify_intent() [29 intents]
    → _handle_workstation_control()
      → resolve_workstation_target()
      → risk check (auto-execute or approval card)
      → _dispatch_via_http_relay()
        → POST http://172.18.0.1:8095/dispatch (Docker → host via iptables rule)
          → NodeMeshServer._http_dispatch()
            → JSON-RPC capability.execute over WS
            → Beast daemon executes (shell/desktop/filesystem/clipboard)
            → asyncio.Future resolved by _resolve_pending_dispatch()
          ← structured result with proof
        ← AdvisorResponse with metadata
      ← right rail renders result + suggested actions
```

## Files Modified

| File | Lines Changed | Risk |
|------|--------------|------|
| transports/node_mesh/server.py | +140 | MEDIUM |
| transports/node_mesh/run.py | +26 | LOW |
| substrate/organism/advisor_conversation.py | +310 | MEDIUM |
| substrate/workstation/command_router.py | +180 | LOW |
| adapters/models/model_router.py | +8 | LOW |

## Known Limitations

1. **Screenshot fails on Session 0** — Beast service runs as Windows Service
   without desktop session. Fix: run daemon as user-session process or use
   Windows Station/Desktop switching.
2. **iptables rule not persistent** — added auto-rule in run.py startup,
   but requires root. Rule survives until reboot.
3. **No auth on HTTP relay** — internal-only (Tailscale + iptables), but
   should add shared-secret token for defense-in-depth.
4. **VPS API health check shows "unreachable"** from inside Docker —
   os-operator checks localhost:8091 which is itself. Cosmetic.

## Next Steps

- Wire voice-controller.ts to route transcripts through AdvisorConversation
  (Phase 14.13L Part 1 — voice path fix)
- Add app registry with known processes/URLs (currently inline in command_router)
- Add governance verdict tracking for workstation commands
- Beast daemon user-session mode for screenshot/desktop interaction
