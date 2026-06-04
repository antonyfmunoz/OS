# UMH Code-Resolved Substrate Canon

Phase: 14.6B-UMH
Status: DRAFT

## Architectural Position

`substrate/` is the innermost UMH layer. It never imports from `transports/`, `services/`, or `projections/`. When substrate needs transport functionality, it defines an abstract port in `substrate/sockets/` and the concrete implementation registers at startup.

Dependency direction (one-way downward):
```
projections/ -> transports/ -> adapters/ -> substrate/
```

## Key Packages and Files

### Type System

- **`substrate/types.py`** -- 1,400 lines, single Pydantic type system
- **`substrate/canonical_types.py`** -- registry of 197 canonical types across 7 modules
- Types include: SignalEnvelope, RiskClass, CapabilityStatus, TaskType, ModelProvider, WorkPacketStatus, RuntimeClass, WorkcellRole, and 180+ others

### Control Plane (`substrate/control_plane/`)

| File | LOC | Role |
|---|---|---|
| `runtime/gateway.py` | 1,927 | Gateway class -- primary control plane entry |
| `runtime/cognitive_loop.py` | 1,539 | Cognitive processing loop |
| `governance.py` | 279 | Deterministic risk classification |
| `router.py` | -- | Signal lifecycle orchestration |
| `runtime/substrate_gateway.py` | -- | SignalEnvelope API surface |

### Execution (`substrate/execution/`)

| File | LOC | Role |
|---|---|---|
| `spine.py` | 522 | 8-stage execution pipeline |
| `trace.py` | 126 | Trace recording + Neon persistence |
| `feedback.py` | 85 | Quality scoring + learning loop |
| `bridge/` | -- | Session management, mode routing, voice |
| `ingestion/` | -- | Canonical ingestion pipeline |
| `runtime/` | -- | Capability routing, worker contracts |

### Organism (`substrate/organism/`)

The largest substrate package, implementing the self-organizing execution economy.

- **201 files**, **70,126 lines**
- Runtime graph, coordinator, workcell protocol
- Execution economics, recursion governance, advisor hierarchy
- Capability-aware routing, autonomous tick, orchestration loop

### State (`substrate/state/`)

- **64 files** managing persistence
- `context/context.py` -- SubstrateContext (identity), load_context_from_env()
- Memory stores (conversation, agent, canonical)
- Storage adapters, config management, session state

### Governance (`substrate/governance/`)

- **19 files** implementing governed execution
- Risk classes: NEGLIGIBLE, LOW, MEDIUM, HIGH, CRITICAL
- Policy engine, authority validation, quality gates
- Accountability tracking

### Sockets (`substrate/sockets/`)

- **19 files** defining abstract ports
- `notification.py` -- abstract notification port (transports register at boot)
- `channel_port.py` -- abstract channel router port
- Signal, capability, outcome, and view ports

### Understanding (`substrate/understanding/`)

- **54 files** covering perception and interpretation
- Deliberation council for multi-perspective evaluation
- Knowledge retrieval and graph queries
- Perception pipeline (signal intake, classification)
- Ontology layer (primitives, relationships, laws)

## Pre-Commit Gates

Four scripts enforce architectural laws at every commit:

| Script | Law Enforced |
|---|---|
| `scripts/check_type_divergence.py` | Type Coherence -- no parallel types |
| `scripts/check_instance_leak.py` | Instance Context -- no hardcoded identity |
| `scripts/check_projection_leak.py` | Projection Boundary -- no projection names in substrate/ |
| `scripts/check_dependency_direction.py` | Architecture Layers -- one-way downward dependencies |

Each gate blocks the commit on violation. Full codebase scan available via `--all` flag.
