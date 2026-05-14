# Phase 96.8M -- Discord Interface Adapter v1

**Date:** 2026-05-07
**Status:** COMPLETE
**Gate:** DISCORD_INTERFACE_ADAPTER_V1
**Next Gate:** CONTROL_PLANE_ROUTER_V1

---

## What This Is

A minimal Discord bot that bridges Discord commands to the Local
Worker Runtime Daemon via filesystem work packets. Discord is an
interface adapter -- it translates user intent into structured
packets and relays proof results back.

## What This Is NOT

- NOT an orchestrator
- NOT a control plane
- NOT an autonomous agent
- NOT a memory system
- NOT a scheduler
- NOT a decision-making layer

Discord does not decide what work to do. It does not plan, reason,
or self-improve. It accepts exactly three commands (!ping, !chrome,
!status) and forwards them as work packets.

---

## Separation of Concerns

| Layer | Component | Responsibility |
|-------|-----------|---------------|
| Interface | Discord adapter | Translate user commands into work packets |
| Control | (future) Control plane router | Resolve capabilities, route to workers |
| Runtime | Local worker daemon | Execute packets, route to adapters, emit proof |
| Adapter | Windows PS relay | Perform environment-native GUI actions |

The Discord adapter writes to the daemon's inbox. The daemon routes
to the correct adapter. The adapter performs the action. Proof flows
back through the proof directory. The Discord adapter polls for
proof and replies.

---

## Why filesystem_json Still Works

The Discord adapter writes a JSON file to the daemon inbox.
The daemon picks it up on its next poll cycle. Proof files appear
in the proof directory. The Discord adapter polls for the matching
proof.

This is sufficient because:
- Single interface, single worker, single adapter
- Latency tolerance is seconds, not milliseconds
- Files are inspectable and debuggable
- Zero additional dependencies

---

## Supported Commands

| Command | Action | Adapter |
|---------|--------|---------|
| !ping | Relay health check | windows_interactive_desktop_relay |
| !chrome | Open Chrome at hardcoded safe URL | windows_interactive_desktop_relay |
| !status | Report adapter state | (local, no packet) |

!chrome uses the hardcoded URL https://drive.google.com/drive/my-drive.
No arbitrary URLs are accepted. No shell execution. No arbitrary
commands.

---

## Files Created

| File | Purpose |
|------|---------|
| eos_ai/interfaces/discord_interface_adapter_v1.py | Discord bot interface adapter |
| config/discord_interface_adapter_v1.json | Adapter config |
| tests/test_discord_interface_adapter_v1.py | 25 adapter tests |
| docs/system/phase968m_discord_interface_adapter_v1_report.md | This report |

## Directories Created

| Directory | Purpose |
|-----------|---------|
| eos_ai/interfaces/ | Interface adapter modules |
| data/runtime/discord_interface_adapter/ | Adapter state |
| data/runtime/discord_interface_adapter/logs/ | Adapter logs |
| data/runtime/discord_interface_adapter/processed/ | Processed packets |
| data/runtime/discord_interface_adapter/failed/ | Failed packets |

---

## Tests Passed

| Test File | Tests | Status |
|-----------|-------|--------|
| test_discord_interface_adapter_v1.py | 25 | ALL PASS |

Test coverage:
- Command parsing (supported + unsupported)
- Unsupported command rejection (returns None)
- Work packet generation (ping + chrome)
- Chrome URL is hardcoded safe value
- Chrome blocked launch methods enforced
- Packet written to inbox correctly
- Proof formatting (completed, timeout, failed, window title)
- Proof polling (finds match, times out, ignores non-match)
- Malformed proof file skipped without crash
- Config loading
- Adapter initializes without token (no crash)
- No arbitrary shell/exec/url commands

---

## Future Interface Adapters

| Interface | When | Purpose |
|-----------|------|---------|
| Telegram | After Discord proven | Founder mobile access |
| Web UI | After control plane | Browser-based dashboard |
| REST API | After control plane | Programmatic access |
| Voice | After substrate matures | Spoken commands |
| Mobile app | After web UI | Native mobile |

Each future interface adapter follows the same pattern: translate
user intent into work packets, submit to daemon inbox, poll for
proof, relay results back through the interface.

---

## Future Control-Plane Evolution

The current flow is: interface -> daemon inbox -> adapter -> proof.
There is no control plane yet. The daemon routes directly based
on the adapter registry.

Future control plane adds:
- Capability resolution (can this worker handle this?)
- Authority verification (does the adapter have authority?)
- Rate limiting and governance
- Multi-worker coordination
- Proof aggregation and audit trail

The interface adapter does not change when the control plane is
added. It still writes packets and polls for proof. The control
plane sits between the inbox and the daemon.

---

## What Was Not Executed

| Item | Status |
|------|--------|
| Discord bot started | NO (no token in test env) |
| Chrome opened | NO |
| Drive/Docs accessed | NO |
| Screenshots captured | NO |
| Tokens/cookies captured | NO |
| Memory promoted | NO |
| Autonomous planning | NO |
| LLM calls made | NO |

---

## Next Gate: CONTROL_PLANE_ROUTER_V1

Build a small deterministic control-plane router that receives
interface requests, resolves capability + authority + adapter
routing, dispatches to worker runtimes, and tracks RuntimeProof
traces without adding autonomous planning layers.
