# UMH Dependency Graph — Phase 75A

> Generated: 2026-05-02 | Modules: 734 | Edges: 1963 | Packages: 52

---

## Summary

The UMH codebase contains 734 Python modules across 52 packages, with
1963 internal import edges. The dependency structure reveals a clear
layered architecture with some notable coupling hotspots.

---

## Package-Level Dependency Clusters

### Core Infrastructure (high fan-in, few deps)
- `umh.core` — clock, config, logging. Imported by nearly everything (68 imports to `core.clock`).
- `umh.storage` — Neon adapter. Second most imported (52 fan-in).
- `umh.events` — event stream. 17 fan-in.

### Execution Spine
- `umh.execution` — engine, contract, stages, approval, harness, pipeline, quality, observability.
- `umh.capability` — registry and router for execution resources.
- `umh.governance` — authority, governor, capability gating.
- `umh.adapters` — platform bridges (LLM, browser, discord, notion, workstation, voice).

### Intelligence Kernel (Phases 30-74)
- `umh.runtime` — 65 files. Regime classification, pattern matching, adaptive learning, half-life,
  weight evolution, trajectory, simulation, identity. The reality mimicry organism.
- `umh.reasoning` — causal attribution, influence scoring, meta control, convergence.
- `umh.analytics` — exploration engine, score distribution, strategy synthesis.
- `umh.prediction` — calibrator, evaluator, predictor, temporal, weights.
- `umh.model` — behavior model, aggregator, traits.

### Runtime Engine (legacy EOS layer)
- `umh.runtime_engine` — 147 files. Original eos_ai modules migrated to UMH namespace.
  Contains cognitive_loop, agent_runtime, model_router, gateway, session_runtime, etc.
  Highest coupling: `session_runtime` (38 fan-out), `execution_spine` (13 fan-out).

### Substrate (operator/workstation layer)
- `umh.substrate` — 170 files. Discord/voice/meeting intelligence, operator sessions,
  task pipeline, execution workers, presence, station runtime.

### Control Plane
- `umh.control` — FastAPI HTTP API + CLI. 32 fan-out from `control.api`.

### Domain Logic
- `umh.signal` — ingestion, hierarchy, routing, sensitivity.
- `umh.intent` — compiler, compiler_ext.
- `umh.world` — world model, calibration, dynamics, simulation, state.
- `umh.memory` — context, embedder, hooks, metrics, persistent store, storage.
- `umh.goals` — engine, state, alignment, arbitrator, budget, credit, evaluator, policy.
- `umh.planning` — planner, hierarchical planning, directive engine, quality, validator.
- `umh.strategy` — decomposer, scoring, refiner, memory, templates.
- `umh.feedback` — outcome evaluator, outcome feedback, dynamics.

### Supporting Packages
- `umh.protocols` — typed contract interfaces for all subsystem boundaries.
- `umh.jobs` — lifecycle, locking, persistence, priority.
- `umh.nodes` — distributed nodes, heartbeat, failover, SSH transport.
- `umh.cells` — cell runtime, orchestrator, persistence, workflow.
- `umh.environments` — containers, sandbox, scheduler, telemetry.
- `umh.scheduler` — policy, runner, store.
- `umh.interfaces` — Discord bot, Telegram bot, webhooks.

---

## Top Fan-In (most imported — system foundations)

| Count | Module | Role |
|-------|--------|------|
| 68 | `umh.core.clock` | Timestamp utility |
| 52 | `umh.storage.adapters.neon` | Neon DB adapter |
| 51 | `umh.environments.system_context` | Environment detection |
| 17 | `umh.events.stream` | Event bus |
| 16 | `umh.workstation.business` | Business instance context |
| 16 | `umh.goals.state` | Goal registry |
| 13 | `umh.gateway.entry` | Signal entry point |
| 11 | `umh.execution.stages` | Execution stage types |
| 10 | `umh.execution.contract` | Execution request/result types |
| 10 | `umh.execution.engine` | Single execution entry point |
| 10 | `umh.strategy.memory` | Strategy performance tracking |
| 10 | `umh.decision.trace` | Decision audit trail |

---

## Top Fan-Out (most imports — integration points / potential god modules)

| Count | Module | Risk |
|-------|--------|------|
| 59 | `umh.interfaces.discord.bot` | Interface — expected |
| 38 | `umh.runtime_engine.session_runtime` | HIGH — needs decomposition |
| 33 | `umh.interfaces.telegram.bot` | Interface — expected |
| 32 | `umh.control.api` | Control plane — expected |
| 23 | `umh.control.cli` | CLI — expected |
| 17 | `umh.runtime.advisor` | Intelligence aggregator |
| 15 | `umh.run` | 9-stage run loop |
| 13 | `umh.runtime_engine.execution_spine` | Legacy execution wiring |

---

## Package-Level Cycles (23 detected)

Key cycle families:

1. **runtime_engine <-> planning <-> persistence_layer <-> substrate**
   The legacy runtime engine and substrate both reference planning/persistence.

2. **execution <-> adapters**
   Bidirectional coupling between execution engine and adapter layer.

3. **adapters <-> runtime_loop <-> protocols**
   Runtime loop lifecycle references protocols which reference adapters.

4. **goals <-> strategy <-> planning** (through protocols)
   Goal-strategy-planning triangle via protocol definitions.

5. **substrate <-> world <-> memory <-> orchestrator <-> execution <-> adapters**
   Long chain through the operator layer to core execution.

### Remediation Priority
- **execution <-> adapters**: Break with dependency inversion (adapters implement protocols, execution depends on protocols only).
- **runtime_engine <-> substrate**: Extract shared types to protocols package.
- **goals <-> strategy <-> planning**: Already partially mediated by protocols — complete the extraction.

---

## Boundary Violations (10 detected)

All violations are `subprocess` imports outside allowed layers:

| Module | Issue |
|--------|-------|
| `umh.interfaces.discord.bot` | subprocess import (2x) |
| `umh.interfaces.telegram.bot` | subprocess import |
| `umh.runtime_engine.cc_sdk` | subprocess import |
| `umh.runtime_engine.email_gps` | subprocess import |
| `umh.runtime_engine.gws_connector` | subprocess import |
| `umh.runtime_engine.notebooklm_sync` | subprocess import |
| `umh.runtime_engine.orchestrator` | subprocess import |
| `umh.runtime_engine.system_health` | subprocess import |
| `umh.runtime_engine.voice_engine` | subprocess import |

**Assessment**: Most are in `runtime_engine` (legacy EOS layer) and `interfaces` (bot startup).
These are not PRD-critical violations for MVP but should be migrated to adapter layer long-term.

---

## Architecture Shape

```
                    ┌─────────────┐
                    │  Interfaces  │  (Discord, Telegram, Webhooks)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Gateway    │  (UMHInput → translate_and_run)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ Control Plane│  (FastAPI + CLI)
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌──▼───┐ ┌──────▼──────┐
       │   Signal     │ │Intent│ │    World     │
       │  Ingestion   │ │Compile│ │   Model     │
       └──────┬──────┘ └──┬───┘ └──────┬──────┘
              └────────────┼────────────┘
                           │
                    ┌──────▼──────┐
                    │  Decision +  │  (Goals, Strategy, Planning)
                    │  Intelligence│  (Runtime kernel: phases 30-74)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Governance  │  (Authority, Safety)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Execution   │  (Engine, Spine, Stages)
                    │  + Capability│  (Registry, Router)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Adapters   │  (LLM, Browser, Shell, etc.)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ Environments │  (Sandbox, Container, System)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Feedback +  │  (Outcome → Learning → Memory)
                    │  Observability│
                    └─────────────┘
```

---

## Data Source

Full module-level graph in `docs/system/dependency_data.json` (1963 edges).
Generated by `scripts/phase75a_dep_scanner.py`.
