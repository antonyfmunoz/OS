# execution/

All work execution. Workers, runtimes, environments, transport,
actuation, and the execution spine.

## Subdirectories

| Path | Purpose |
|------|---------|
| `actuation/` | Physical/digital actuation layer |
| `agents/` | Agent execution runtime |
| `engine/` | Execution engine core |
| `environments/` | Environment definitions and bridges |
| `loop/` | Execution loop machinery |
| `media/` | Media processing (voice, video) |
| `runtime/` | Execution runtime (model_router, agent_runtime, spine) |
| `tasks/` | Task execution tracking |
| `transport/` | Transport layer (sessions, storage, station daemon) — §24 canonical location |
| `voice/` | Voice execution pipeline |
| `workers/` | Worker implementations (workstation, etc.) |
| `workflows/` | Workflow execution |

## §24 Reference

Canonical module tree §24: `execution/` — actions, work_packets, queue,
dag, workers, environments, actuation, runtime.

## Boundary

Execution performs work authorized by the control plane. It does NOT
make governance decisions or access external systems directly (adapters
handle that). Transport (`execution/transport/`) is execution
infrastructure, migrated from `runtime/transport/` on 2026-05-14.
