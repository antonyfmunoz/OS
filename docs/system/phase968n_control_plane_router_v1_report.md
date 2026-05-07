# Phase 96.8N -- Control Plane Router v1

**Date:** 2026-05-07
**Status:** COMPLETE
**Gate:** CONTROL_PLANE_ROUTER_V1
**Previous Gate:** DISCORD_INTERFACE_ADAPTER_V1

---

## What This Is

A deterministic, stateless control plane router that receives
WorkPackets, resolves capability requirements, selects the
correct adapter via the AdapterRegistry, delegates execution
to the worker runtime daemon, and returns a normalized
RouterResult with RuntimeProof reference.

## What This Is NOT

- NOT an orchestrator
- NOT an agent
- NOT a planner
- NOT a memory system
- NOT an LLM caller
- NOT a decision-making layer

The router does not decide WHAT to do. It resolves HOW to
route a request that an interface has already validated.

---

## Why Router != Orchestrator

An orchestrator coordinates multi-step workflows, manages
state across steps, handles failures with retries and fallbacks,
and may invoke planning logic.

The router does exactly one thing: given a WorkPacket, resolve
which runtime and adapter should handle it, submit it, wait
for proof, and return the result. One packet in, one result out.
No loops. No retries. No state between calls.

## Why Router != Agent

An agent reasons about goals, selects actions, learns from
outcomes, and may invoke LLMs. The router has a fixed
ACTION_CAPABILITY_MAP and delegates to the AdapterRegistry.
There is no reasoning. There is no learning. The same input
always produces the same routing decision.

## Why This Matters for Substrate Evolution

Before the router:
- Discord adapter built work packets directly
- Discord adapter wrote to the daemon inbox directly
- Discord adapter polled for proof directly
- Every new interface would duplicate this logic

After the router:
- Interfaces submit a WorkPacket
- Router resolves capability, adapter, and runtime
- Router handles inbox write and proof polling
- Interfaces get a normalized RouterResult
- New interfaces need zero routing knowledge

The router is the seam between "what the user wants" and
"who can do it." Adding a new adapter, a new runtime, or
a new interface changes one layer without touching the others.

---

## Architecture

```
Interface (Discord, Telegram, REST, etc.)
  |
  v
WorkPacket
  |
  v
ControlPlaneRouterV1
  |-- validate_packet()
  |-- resolve_capability()  (ACTION_CAPABILITY_MAP)
  |-- resolve_adapter()     (AdapterRegistry)
  |-- resolve_runtime()     (config default or packet override)
  |-- _write_to_inbox()     (daemon filesystem inbox)
  |-- _poll_for_proof()     (proof directory)
  |
  v
RouterResult
  |-- router_status
  |-- router_decision
  |-- runtime_proof_reference
  |-- execution_trace_id
  |-- timestamps
```

## Routing Lifecycle

1. Interface builds a WorkPacket (packet_id, action_type, payload)
2. Router validates the packet (required fields, allowed action types)
3. Router resolves capability requirement from ACTION_CAPABILITY_MAP
4. Router queries AdapterRegistry for an adapter that handles the action
5. Router determines runtime target (default or packet-specified)
6. Router writes daemon-format packet to the inbox directory
7. Router polls proof directory for matching RuntimeProof
8. Router wraps proof into a normalized RouterResult
9. Interface receives RouterResult and formats for its channel

## Authority Boundaries

The router enforces the same authority model as the lower layers:
- `ping` requires `local_shell` authority
- `open_application_url` requires `local_gui` authority
- The AdapterRegistry maps these requirements to specific adapters
- The router does not override authority — it queries the registry

---

## Contracts

| Contract | Purpose |
|----------|---------|
| WorkPacket | Incoming request from any interface |
| CapabilityRequirement | What the action needs (GUI, shell, authority) |
| RouterDecision | Which runtime/adapter was selected |
| RuntimeProofReference | Pointer to the RuntimeProofRecord |
| RouterResult | Normalized result for the interface |
| RouterStatus | Enum: ROUTED, COMPLETED, FAILED, REJECTED, TIMEOUT, NO_ADAPTER, NO_RUNTIME, INVALID_PACKET |
| CapabilityType | Enum: SHELL_EXECUTION, WINDOWS_GUI_EXECUTION |

## Supported Actions

| Action | Capability | Adapter |
|--------|-----------|---------|
| ping | shell_execution | windows_interactive_desktop_relay |
| open_application_url | windows_gui_execution | windows_interactive_desktop_relay |

---

## Files Created

| File | Purpose |
|------|---------|
| core/control_plane_router/router_contracts.py | Typed routing contracts |
| core/control_plane_router/control_plane_router_v1.py | Router implementation |
| config/control_plane_router_v1.json | Router configuration |
| tests/test_control_plane_router_v1.py | 36 router tests |
| docs/system/phase968n_control_plane_router_v1_report.md | This report |

---

## Tests Passed

| Test File | Tests | Status |
|-----------|-------|--------|
| test_control_plane_router_v1.py | 36 | ALL PASS |

Test coverage:
- Packet validation (valid, missing fields, disallowed actions)
- Capability resolution (ping, chrome, unknown)
- Adapter resolution (ping, chrome, unknown)
- Runtime resolution (default, explicit override)
- Dry-run routing (ping, chrome, invalid, unknown, no adapter)
- Full route with proof (completed, timeout, failed)
- Malformed packet handling
- Deterministic routing (same input = same output, stateless)
- RouterResult structure (timestamps, trace ID, error messages)
- Config loading
- Allowed action types
- Capability map consistency

---

## Integration Points

| Component | Integration |
|-----------|------------|
| AdapterRegistry | Router queries for adapter selection |
| WorkerRuntimeContracts | ProofStatus enum for proof interpretation |
| Local Worker Daemon | Router writes to daemon inbox, reads proof dir |
| Discord Interface | Can submit WorkPackets through the router |

---

## What Was Not Executed

| Item | Status |
|------|--------|
| Chrome opened | NO |
| Drive/Docs accessed | NO |
| Screenshots captured | NO |
| Tokens/cookies captured | NO |
| Memory promoted | NO |
| Autonomous planning | NO |
| LLM calls made | NO |
| Daemon started | NO |
| Discord bot started | NO |

---

## Future Evolution

| Enhancement | When | Purpose |
|-------------|------|---------|
| Authority verification | After multi-adapter | Enforce authority before routing |
| Rate limiting | After multi-interface | Prevent abuse |
| Multi-runtime routing | After VPS worker | Route to remote runtimes |
| Proof aggregation | After multi-step | Combine proofs from chains |
| Audit trail | After governance | Log all routing decisions |
| Capability discovery | After dynamic adapters | Runtime capability negotiation |

Each enhancement extends the router without changing its core
contract: WorkPacket in, RouterResult out. The interfaces and
adapters remain unchanged.
