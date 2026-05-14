# Phase 96.8O -- Wire Discord Interface Through Control Plane Router

**Date:** 2026-05-07
**Status:** COMPLETE
**Gate:** DISCORD_THROUGH_ROUTER
**Previous Gate:** CONTROL_PLANE_ROUTER_V1

---

## What Changed

The Discord interface adapter no longer knows how to:
- Build daemon-format packets
- Write to the daemon inbox
- Poll the proof directory
- Select adapters or runtimes

It now does exactly two things:
1. Translate a Discord command into a WorkPacket
2. Format a RouterResult into a Discord reply

Everything between those two steps is the router's job.

---

## Before (Phase 96.8M)

```
Discord !ping
  → build_work_packet("!ping")     # Discord knows packet format
  → write_work_packet(packet, inbox) # Discord knows inbox path
  → poll_for_proof(id, proof_dir)    # Discord knows proof dir
  → format_proof_summary(proof)      # Discord reads raw proof
```

## After (Phase 96.8O)

```
Discord !ping
  → build_work_packet_for_router("!ping")  # Discord builds WorkPacket
  → router.route_work_packet(work_packet)   # Router owns everything
  → format_router_result(result, "!ping")   # Discord reads RouterResult
```

---

## Why Discord Is Now a Thin Interface

Discord does not need to know:
- Where the daemon inbox is
- What format the daemon expects
- Which adapter handles ping vs chrome
- Where proof files are stored
- How to interpret raw proof JSON

It only needs to know:
- Which commands map to which action types (COMMAND_ACTION_MAP)
- How to build a WorkPacket with the right payload
- How to format a RouterResult for Discord's markdown

This is the correct boundary. When Telegram, REST, or
web interfaces are added, they follow the same pattern:
translate user intent → WorkPacket → router → RouterResult →
format for channel.

---

## Why Router != Orchestrator (Reinforced)

This refactor proves the distinction concretely:
- The router is called once per command
- The router returns once per command
- There is no loop, no retry, no multi-step coordination
- The router does not remember previous calls
- The router does not modify its behavior based on outcomes

An orchestrator would coordinate sequences (open Chrome, THEN
check window, THEN take screenshot). The router routes a single
packet to a single runtime and returns a single result.

---

## How This Returns to W0 Chrome/Drive Test

With Discord wired through the router, the next phase can:
1. Discord !chrome → WorkPacket(action_type="open_application_url")
2. Router resolves → windows_interactive_desktop_relay
3. Daemon routes → PowerShell relay
4. Relay opens Chrome at hardcoded Drive URL
5. Proof flows back through the canonical path
6. RouterResult with RuntimeProofReference returns to Discord

This is the same Chrome/Drive test from Phase 96.8, but now
flowing through the full interface → router → daemon → adapter
→ proof → result pipeline. No shortcuts. No direct wiring.

---

## Files Changed

| File | Change |
|------|--------|
| eos_ai/interfaces/discord_interface_adapter_v1.py | Wired through ControlPlaneRouterV1 |
| tests/test_discord_interface_adapter_v1.py | Added 17 router integration tests |
| docs/system/phase968o_discord_through_router_report.md | This report |

## New Exports

| Export | Purpose |
|--------|---------|
| COMMAND_ACTION_MAP | Maps Discord commands to action types |
| build_work_packet_for_router() | Builds WorkPacket from Discord command |
| format_router_result() | Formats RouterResult for Discord reply |

## Retained Exports (Legacy)

| Export | Status |
|--------|--------|
| build_work_packet() | Retained for standalone/test use |
| write_work_packet() | Retained for standalone/test use |
| poll_for_proof() | Retained for standalone/test use |
| format_proof_summary() | Retained for standalone/test use |

---

## Tests Passed

| Test File | Tests | Status |
|-----------|-------|--------|
| test_discord_interface_adapter_v1.py | 42 (25 legacy + 17 new) | ALL PASS |
| test_control_plane_router_v1.py | 36 | ALL PASS |
| test_worker_runtime_contracts.py | 15 | ALL PASS |
| test_adapter_registry_contracts.py | 14 | ALL PASS |
| test_local_worker_runtime_daemon.py | 14 | ALL PASS |
| **Total** | **121** | **ALL PASS** |

New test coverage:
- COMMAND_ACTION_MAP correctness
- WorkPacket builder (ping, chrome, unknown, empty, status)
- Chrome WorkPacket payload retains safe URL
- RouterResult formatting (completed, timeout, invalid, no adapter, failed)
- Adapter initializes with router instance
- Router respects config timeout

---

## What Was Not Executed

| Item | Status |
|------|--------|
| Chrome opened | NO |
| Drive/Docs accessed | NO |
| Discord bot started | NO |
| Daemon started | NO |
| LLM calls made | NO |
| Memory promoted | NO |
| Secrets captured | NO |

---

## Next Gate: W0_ROUTED_CHROME_VISIBLE_RERUN

Run the Chrome visible proof through the canonical
interface → router → daemon → adapter → proof → result
pipeline, then return to the W0 Google Drive/Docs test.
