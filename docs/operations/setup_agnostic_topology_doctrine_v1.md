# Setup-Agnostic Topology Doctrine v1

**Phase**: 94D.4 — Auto Worker Runtime + Topology Boundary
**Status**: ACTIVE
**Date**: 2026-05-04

---

## Doctrine

UMH does not assume any specific hardware topology. The system discovers
what the user has during onboarding and routes work based on capabilities,
not node names.

## Core Principles

1. **No hardcoded VPS assumption.** A user with only a laptop runs UMH
   on that laptop. The orchestrator is wherever the user puts it.

2. **No hardcoded node names.** Work orders route to capabilities
   (e.g., "gui_computer_use"), not to "local_pc_worker" or "vps_orchestrator".

3. **Topology is discovered, not prescribed.** The onboarding flow asks
   what machines the user has, what they can do, and how they connect.

4. **Missing capability = SETUP_REQUIRED, not failure.** If a task needs
   GUI computer use but no node has it, the system says "you need a
   GUI-capable node" — not "error: node not found."

5. **Any topology is valid.** Single laptop. VPS + local PC. Multi-cloud.
   Phone-only. The contracts support all of them.

## Contracts

- `TopologyProfile` — the full map of a user's nodes
- `NodeProfile` — one machine with its type, roles, capabilities
- `InterfaceProfile` — one interface (CLI, Discord, etc.) attached to a node
- `TransportProfile` — one connection method between nodes

## Reference Topologies

| Topology | Nodes | Use Case |
|----------|-------|----------|
| `build_founder_current_topology()` | VPS + Local PC | Founder's actual setup |
| `build_single_local_topology()` | 1 local machine | New user, simplest case |

## File

`eos_ai/substrate/topology_contracts.py`
