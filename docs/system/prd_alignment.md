# PRD Alignment Map — Phase 75A

> Generated: 2026-05-02 | Based on ARCHITECTURE.md + actual codebase inspection

---

## PRD Domain Status Overview

| Domain | Status | Modules | MVP Relevance | Notes |
|--------|--------|---------|---------------|-------|
| core | IMPLEMENTED | 13 | CRITICAL | Clock, config, events, gateway fully operational |
| protocols | IMPLEMENTED | 14 | CRITICAL | All subsystem contracts defined |
| interpretation (signal/intent) | IMPLEMENTED | 36 | CRITICAL | Signal ingestion, intent compiler, reasoning all present |
| world_model | IMPLEMENTED | 9 | CRITICAL | Two-layer model with calibration, dynamics |
| memory | IMPLEMENTED | 8 | CRITICAL | Storage, embedder, hooks, context |
| profiles | IMPLEMENTED | 9 | HIGH | Behavior model, traits, brain context |
| planning | IMPLEMENTED | 48 | HIGH | Goals, strategy, hierarchical planning, orchestration |
| capabilities | IMPLEMENTED | 11 | CRITICAL | Registry, router, tool registry |
| execution | IMPLEMENTED | 73 | CRITICAL | Engine, contract, stages, pipeline, approval, runtime loop |
| governance | IMPLEMENTED | 7 | CRITICAL | Authority, governor, capability gating |
| adapters | IMPLEMENTED | 30 | CRITICAL | LLM, browser, voice, discord, notion, workstation |
| environments | IMPLEMENTED | 10 | HIGH | Containers, sandbox, scheduler, telemetry |
| learning | OVERBUILT | 36 | LOW | Phases 19-74 built extensive learning/prediction |
| runtime (intelligence kernel) | OVERBUILT | 223 | MEDIUM | 65 runtime + 147 runtime_engine + 11 nodes |
| presence/workstation | PARTIAL | 173 | MEDIUM | Substrate=170, workstation=3. Operator layer rich, workstation thin |
| observability | PARTIAL | 5 | HIGH | execution.observability + execution.metrics + events.stream. Needs formal trace export |
| security | STUB | 3 | HIGH | Access control + execution guard exist but minimal |
| distribution | MISSING | 0 | LOW | No distribution/packaging system |
| onboarding | STUB | 1 | LOW | runtime_engine.onboarding_backfill only |
| interface | IMPLEMENTED | 19 | MEDIUM | Discord + Telegram + webhooks |
| registry | PARTIAL | 5 | HIGH | Multiple registries (adapter, capability, pattern, tool) but no unified service registry |
| storage | IMPLEMENTED | 7 | CRITICAL | Neon adapter + backend abstraction |
| ontology | PARTIAL | 2 | LOW | primitives.ontological exists but thin |
| control_plane | IMPLEMENTED | 5 | CRITICAL | FastAPI API + CLI + identity. Core PRD requirement met |

---

## Detailed Domain Analysis

### Control Plane — IMPLEMENTED
**Files**: `umh/control/api.py`, `umh/control/cli.py`, `umh/control/identity.py`
**Status**: FastAPI HTTP API with identity-based auth, execution dispatch, approval management, event streaming.
**Gap**: No SSE/WebSocket live streaming in production. Identity store is in-memory.
**MVP Action**: Wire as the single entry point for all external interaction. Persist identity store.

### Ontology — PARTIAL
**Files**: `umh/primitives/ontological.py`
**Status**: 13 primitives defined from original EOS. Not wired into UMH run loop.
**Gap**: No typed ontology registry. Primitives not used in signal classification.
**MVP Action**: Not required for MVP. Preserve for post-MVP enrichment.

### Protocols — IMPLEMENTED
**Files**: 14 protocol modules covering adapters, capabilities, execution, governance, interpretation, memory, outcome, persistence, planning, security, signals, workstation, world.
**Status**: Canonical contract definitions for all subsystem boundaries. Well-structured.
**Gap**: Some subsystems still import concrete implementations instead of protocols.
**MVP Action**: Enforce protocol-first imports in new code. No changes to existing.

### Interpretation / Decomposition — IMPLEMENTED
**Files**: `umh/signal/` (7), `umh/intent/` (3), `umh/context/` (4), `umh/attention/` (4), `umh/reasoning/` (16)
**Status**: Full signal → intent → context pipeline. Reasoning layer has causal attribution, influence scoring, meta control.
**Gap**: Reasoning is decoupled from the run loop (connected through runtime kernel).
**MVP Action**: Signal + intent + context are on the critical path. Reasoning is enhancement.

### World Model — IMPLEMENTED
**Files**: `umh/world/` (9)
**Status**: Two-layer model (canonical + instance). Calibration, dynamics adapter, simulation, reasoning.
**Gap**: World model updates are not persisted across restarts.
**MVP Action**: Wire world model read/update into run loop (already in `run.py`). Add persistence.

### Memory — IMPLEMENTED
**Files**: `umh/memory/` (8)
**Status**: Storage backend abstraction, embedder, hooks, context, metrics, persistent store.
**Gap**: Depends on Neon adapter. No local fallback for standalone.
**MVP Action**: On critical path. Storage.get_storage() already resolves backend.

### Profiles — IMPLEMENTED
**Files**: `umh/model/` (4), `umh/brains/` (5)
**Status**: Behavior model, trait tracking, brain context, signal classification.
**Gap**: Not wired into the run loop's context assembly.
**MVP Action**: MVP_SUPPORT. Wire brain context into context builder for enrichment.

### Planning / Composition — IMPLEMENTED
**Files**: `umh/planning/` (11), `umh/goals/` (17), `umh/strategy/` (10), `umh/orchestrator/` (8), `umh/objectives/` (2)
**Status**: Hierarchical planning, goal engine with state/alignment/arbitration, strategy decomposition.
**Gap**: Multiple goal engines (umh.goals.engine, umh.goals.goal_engine). Orchestrator duplicated in runtime_engine.
**MVP Action**: Goals + strategy + planner are on critical path. Orchestrator is support.

### Completeness / Quality — IMPLEMENTED
**Files**: `umh/execution/quality.py`, `umh/planning/quality.py`
**Status**: Execution quality gate and plan quality validation exist.
**Gap**: Not wired as mandatory gates in the run loop.
**MVP Action**: Wire quality.py as post-execution check.

### Capabilities — IMPLEMENTED
**Files**: `umh/capability/` (3), `umh/capabilities/` (2), `umh/tools/` (2)
**Status**: Registry + router + spec. Tools registry for tool-based capabilities.
**Gap**: Two capability packages (capability vs capabilities). Tool registry thin.
**MVP Action**: Consolidate to single capability package. Registry on critical path.

### Adapters — IMPLEMENTED
**Files**: `umh/adapters/` (26+4)
**Status**: Protocol-based adapters for LLM, browser, discord, notion, voice, workstation. Null stubs for standalone.
**Gap**: Model router exists in both adapters and runtime_engine. Bridge discovery works.
**MVP Action**: On critical path. Adapter registry + LLM adapter are minimum required.

### Execution Spine — IMPLEMENTED
**Files**: `umh/execution/` (20), `umh/runtime_loop/` (13), `umh/stages/` (10)
**Status**: Single execute() entry point. Full contract types. Approval system. Pipeline. Observability.
**Gap**: runtime_loop is a parallel execution path (Discord lifecycle) that partially overlaps execution engine.
**MVP Action**: execution.engine.execute() is the canonical path. runtime_loop is for live sessions.

### Environments — IMPLEMENTED
**Files**: `umh/environments/` (10)
**Status**: Container management, sandbox, scheduler, telemetry, system context detection.
**Gap**: system_context is the most-imported module (51 fan-in) — it's environment detection, not just environments.
**MVP Action**: MVP_SUPPORT. Environments not on critical path for harness but needed for safe execution.

### Governance — IMPLEMENTED
**Files**: `umh/governance/` (4), `umh/policy/` (3)
**Status**: Authority levels, governor with risk classification, capability-based gating.
**Gap**: Governor is improvement-focused (proposals, audit trail). Authority gating is in run.py.
**MVP Action**: governance.authority.check_governance() is on critical path (already in run.py).

### Observability — PARTIAL
**Files**: `umh/execution/observability.py`, `umh/execution/metrics.py`, `umh/events/stream.py`
**Status**: Execution observer pattern, metrics collection, event stream.
**Gap**: No formal trace export (OpenTelemetry). No dashboard. RunTrace captures per-run but no aggregation.
**MVP Action**: RunTrace from run.py is sufficient for MVP. Formal observability is post-MVP.

### Learning — OVERBUILT
**Files**: `umh/learning/` (4), `umh/prediction/` (12), `umh/analytics/` (10), `umh/patterns/` (5), `umh/feedback/` (5)
**Status**: Extensive learning subsystem built in phases 19-74. Prediction, calibration, temporal memory, pattern abstraction.
**Gap**: Rich but not wired into the main run loop. Operates through the runtime intelligence kernel.
**MVP Action**: feedback.loop.record_outcome() is on critical path. Rest is enhancement.

### Distribution / Onboarding — MISSING
**Status**: No distribution packaging. onboarding_backfill exists in runtime_engine but is EOS-specific.
**MVP Action**: Not required for MVP. Post-MVP concern.

### Workstation / Presence — PARTIAL
**Files**: `umh/substrate/` (170), `umh/workstation/` (3)
**Status**: Rich operator substrate (Discord sessions, meeting intelligence, voice, task pipeline). Thin workstation profile.
**Gap**: Substrate is deeply EOS-coupled. Workstation profile is minimal.
**MVP Action**: Not on MVP critical path. Substrate is the live operational surface.

---

## Reality Mimicry Enhancement Mapping (Phases 30-74)

### What was built
| Phase Range | Domain | What it does |
|-------------|--------|-------------|
| 30-33 | Arbitration & Meta | Objective arbitration, meta planning, meta learning, goal persistence |
| 34-37 | Identity & Goals | Identity traits, long horizon, goal hierarchy, tradeoff analysis |
| 38-41 | Context & Horizon | Context weighting, temporal context, adaptive smoothing, multi-horizon |
| 42-49 | Regime Intelligence | Regime classification, memory, hysteresis, dynamics, composite regime |
| 50-59 | Outcome & Learning | Outcome feedback, learning control, attribution, feedback selection, strategy orchestration |
| 60-66 | Weighted Decision | Dimension weighting, weight evolution, regime weight evolution, adaptive learning, interactions |
| 67-74 | Pattern Recognition | Pattern recognition, influence, aggregation, temporal patterns, adaptive half-life, confidence |

### PRD domains they enhance
- **interpretation**: Regime classification enriches signal interpretation
- **world_model**: Pattern memory extends world model with learned patterns
- **planning**: Strategy profiles and weighted decisions enhance planning quality
- **learning**: Core learning loop (outcome → weight evolution → prediction)
- **governance**: Stability guard and hysteresis prevent reckless adaptation

### Subordination rules
1. Intelligence kernel ADVISES but does not EXECUTE. All execution routes through execution.engine.
2. Regime classification INFORMS but does not OVERRIDE governance policy.
3. Pattern memory AUGMENTS but does not REPLACE world model facts.
4. Weight evolution is BOUNDED by invariants (min/max, rate limits, half-life).
5. The runtime intelligence kernel plugs into the MVP as an OPTIONAL enhancement layer.

---

## Summary Gaps for MVP

| Gap | Severity | Action |
|-----|----------|--------|
| Identity store is in-memory | HIGH | Add persistence via Neon adapter |
| World model not persisted | MEDIUM | Add save/load to storage backend |
| Observability has no trace export | LOW | RunTrace is sufficient for MVP |
| Quality gates not wired in run loop | MEDIUM | Wire as post-execution check |
| 42 duplicate modules in runtime_engine | MEDIUM | Document, don't migrate yet |
| Security layer is thin | HIGH | Add input validation to control plane |
| No unified service registry | LOW | Multiple registries work for MVP |
