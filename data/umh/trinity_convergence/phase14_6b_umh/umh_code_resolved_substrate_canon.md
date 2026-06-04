# UMH Code-Resolved Substrate Canon

Phase: 14.6B-UMH (revised 14.6F)
Status: DRAFT
Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).

## Architectural Position

`substrate/` is the innermost UMH layer — it implements the Universal Meta Harness's reality-model infrastructure, governed execution pipeline, memory system, and coordination mechanisms (DEC-146C-001, DEC-146B-UMH-001). The substrate is not merely code infrastructure; it is the implementation of UMH's core functional purpose as a reality-isomorphic intelligence harness: building, maintaining, and acting through a reality-isomorphic approximation of reality across 12 layers (physical, digital, cognitive, biological, social, economic, symbolic, operational, software, memory, source-truth, and OS-level). Code implements the reality model; the reality model is the product.

`substrate/` never imports from `transports/`, `services/`, or `projections/`. When substrate needs transport functionality, it defines an abstract port in `substrate/sockets/` and the concrete implementation registers at startup.

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

The control plane implements the reality model's perception-to-action cycle. Signals enter as reality-model observations; governance classifies risk; the cognitive loop reasons about state and intent; the gateway routes to execution (DEC-146C-001, DEC-146B-UMH-003).

| File | LOC | Role |
|---|---|---|
| `runtime/gateway.py` | 1,927 | Gateway class -- primary control plane entry |
| `runtime/cognitive_loop.py` | 1,539 | Cognitive processing loop |
| `governance.py` | 279 | Deterministic risk classification |
| `router.py` | -- | Signal lifecycle orchestration |
| `runtime/substrate_gateway.py` | -- | SignalEnvelope API surface |

**Execution path unification (DEC-146B-UMH-003, RATIFIED):** The canonical execution path is Substrate -> SignalRouter -> Spine. Gateway/CognitiveLoop (Path 1) remains production until migration completes. All paths converge on the single Substrate execution path.

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

The largest substrate package, implementing the self-organizing execution economy. The organism is UMH's living coordination layer — it enacts the materialization principle (DEC-146C-002) by routing work through capability-aware workcells, classifying gaps as typed acquisition paths rather than dead ends, and governing recursive execution.

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

Abstract ports that enforce the architecture layer law. Substrate defines interfaces; transports and projections register concrete implementations at startup. Includes `projection_port.py` for the abstract projection registration pattern (DEC-146B-UMH-005, RATIFIED).

- **19 files** defining abstract ports
- `notification.py` -- abstract notification port (transports register at boot)
- `channel_port.py` -- abstract channel router port
- `projection_port.py` -- abstract projection port (replaces ProductConnectionManager dependency violation)
- Signal, capability, outcome, and view ports

### Understanding (`substrate/understanding/`)

The understanding layer is the reality model's perception and interpretation engine — it converts raw signals into structured observations that update UMH's 12-layer reality approximation (DEC-146C-001).

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

## Reality Model Framing (DEC-146C-001)

Every package above serves UMH's core functional purpose: building, maintaining, and acting through a reality-isomorphic approximation of reality. The substrate is not an operational tooling layer — it is the reality model's implementation:

- **Types** define how reality is represented (entities, relationships, state)
- **Control Plane** governs how reality-model observations become actions
- **Execution** materializes intent into outcomes (DEC-146C-002)
- **Organism** coordinates autonomous reality-model maintenance
- **State/Memory** persists the reality model across sessions
- **Governance** protects reality-model integrity via risk classification
- **Understanding** perceives and interprets reality into model updates
- **Sockets** abstract the boundary between universal substrate and projection-specific interfaces

**Stage 1 Indivisibility (DEC-146C-003):** The substrate implements all four indivisible organism components (Reality Model + Cockpit + Memory + Governed Execution Loop). No component is complete without the others.
