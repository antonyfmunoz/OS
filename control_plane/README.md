# control_plane/

The single coordination layer. Every request flows through here before
reaching execution. Governance checks, identity resolution, routing,
delegation, and orchestration all live in this layer.

## Subdirectories

| Path | Purpose |
|------|---------|
| `actions/` | Action definitions and dispatch |
| `agents/` | Agent coordination and hierarchy |
| `context/` | Request context assembly |
| `coordination/` | Multi-agent coordination |
| `delegation/` | Task delegation logic |
| `events/` | Event bus and signal handling |
| `goals/` | Goal tracking and selection |
| `identity/` | AI identity and persona |
| `invariants/` | System invariant enforcement |
| `onboarding/` | User onboarding flows |
| `orchestrator/` | Orchestration contracts |
| `proactive/` | Proactive action triggers |
| `protocols/` | Protocol definitions |
| `router/` | Request routing |
| `routing/` | Route resolution |
| `runtime/` | Control plane runtime (gateway, cognitive loop) |
| `scheduling/` | Task scheduling |
| `signals/` | Signal processing |
| `strategy/` | Strategic decision layer |

## §24 Reference

Canonical module tree §24: `control_plane/` — runtime, router, actions,
orchestrator, delegation, coordination, scheduling, signals, events.

## Boundary

The control plane coordinates but does NOT execute. It authorizes,
routes, and delegates to `execution/`. It does NOT access external
systems directly — that goes through `adapters/`.
