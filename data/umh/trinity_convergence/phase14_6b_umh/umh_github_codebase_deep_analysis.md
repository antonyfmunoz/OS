# UMH GitHub Codebase Deep Analysis

Phase: 14.6B-UMH
Status: DRAFT
Generated: 2026-06-03

---

## Repository Overview

| Property | Value |
|----------|-------|
| Repository | `/opt/OS` |
| Package | universal-meta-harness v0.1.0 |
| Build system | hatchling |
| Wheel packages | `[substrate]` |
| Total files | ~54,855 |
| Primary language | Python 3.11+ |
| Secondary | TypeScript (cockpit, saas, transports/api/http) |
| Dependencies | See `pyproject.toml`, `requirements.txt` |

---

## Key Directory Inventory

| Directory | Files | LOC (approx) | Purpose |
|-----------|-------|---------------|---------|
| `substrate/` | 696 .py | ~206K | Universal platform core: types, control plane, execution, governance, state, organism, sockets, ontology, understanding |
| `adapters/` | 89 .py | ~18.7K | External system adapters: model routing, GWS, browser, data sources, capabilities |
| `transports/` | 91 files | ~20K | I/O surfaces: Discord, API/HTTP (Hono), presence handlers, node mesh, Python bridges |
| `projections/` | 48 files | -- | Application projections: EOS agents, workflows, configs |
| `cockpit/` | 148 files | -- | Electron + React cockpit UI: panels, stores, components, voice |
| `services/` | 30 files | -- | Deployment entrypoints: discord_bot.py, operator_api.py, webhook |
| `tests/` | 86 files | -- | Test suite: 2,832 test functions |
| `scripts/` | 124 files | -- | Operational tooling: cron, verification, graph rebuild, pre-commit gates |
| `nodes/` | -- | -- | Distributed execution: Windows daemon, environments, work packets |
| `knowledge/` | -- | -- | Wiki, memory palace, concept docs |
| `saas/` | -- | -- | EOS SaaS projection (TypeScript/React) |

---

## Execution Paths

Three distinct execution paths identified:

### 1. Signal-Driven Execution (Production)
```
Discord message -> SignalFactory -> SignalEnvelope -> Gateway -> OrchestratorKernel
  -> IntentClassifier -> Governance (risk) -> Spine (8-stage pipeline) -> Actuation
```
Primary production path. Deterministic intent classification, governed execution.

### 2. Organism Autonomous Execution
```
OperatorLoopCoordinator -> WorkcellProtocol -> WorkUnit dispatch
  -> Capability routing -> Agent execution -> Outcome recording
```
Organism-driven autonomous cadence. Dry-run only without operator approval.

### 3. Direct API Execution
```
HTTP request -> transports/api/http/routes/ -> Python bridge (stdin/stdout JSON)
  -> substrate functions -> JSON response
```
Cockpit and external API consumers. Routes for execution, governance, organism, system, settings.

---

## Architecture Enforcement

### 4 Pre-Commit Gates

| Gate | Script | Enforces |
|------|--------|----------|
| Type Coherence | `scripts/check_type_divergence.py` | No parallel Enum/BaseModel/dataclass definitions |
| Instance Context | `scripts/check_instance_leak.py` | No hardcoded user/org/AI names in substrate/ |
| Projection Boundary | `scripts/check_projection_leak.py` | No projection names (EOS, CreatorOS) in substrate/ |
| Dependency Direction | `scripts/check_dependency_direction.py` | One-way downward: projections -> transports -> adapters -> substrate |

### Dependency Direction Law
```
projections/saas (EOS, CreatorOS)
    v
transports/ (discord, api/http)
    v
adapters/ (models, GWS, browser)
    v
substrate/ (types, control_plane, execution, governance, state, organism)
```

---

## Technical Debt

### Dead Code
- `workstation/` -- 26,671 lines of dead/dormant code (legacy workstation daemon, pre-organism)

### Naming Debt
- 30 files containing "Universal Mastery Hierarchy" string literal
- 503 occurrences of "EntrepreneurOS" across the codebase (72 files grandfathered in `LEGACY_INSTANCE_LEAKS`)
- Projection boundary gate prevents new leaks

### Dormant Code Classifications
Per UMH dormant classification protocol (PROMOTE/MERGE/ISOLATE/ARCHIVE/DELETE), workstation/ code requires formal classification before removal.

---

## Type System

Single canonical type system via `substrate/canonical_types.py` (~80 registered types):

| Location | Types |
|----------|-------|
| `substrate/types.py` | SignalEnvelope, RiskClass, CapabilityStatus, MemoryType, MemoryEntry, 25+ more |
| `substrate/contracts/agent_types.py` | TaskType, ModelProvider |
| `substrate/execution/runtime/capability_router.py` | Capability (28 job capabilities) |
| `substrate/execution/runtime/worker_runtime_contracts.py` | EnvironmentType, AuthorityDomain |
| `nodes/environments/work_packet.py` | WorkPacketRiskLevel, WorkPacketStatus |
| `substrate/organism/` | RuntimeClass, WorkUnitType, WorkcellRole, etc. |

---

## Intelligence Routing

`adapters/models/model_router.py` -- `call_with_fallback()` is the single entry point.

Current fallback chain:
1. cc_sdk (Opus 4.6 via Claude Max subscription, no API cost)
2. Gemini 2.5 Flash (Python SDK)
3. Groq
4. Ollama (gemma3:4b local fallback)

CEO/strategic agents: `agent_type='ceo'` or `force_opus=True` forces best available.

---

## Test Infrastructure

- 86 test files
- 2,832 test functions
- Framework: pytest
- Coverage: substrate/, adapters/, transports/, organism/
- Pre-commit gates run as part of test pipeline

---

## Build Configuration

From `pyproject.toml`:
- Build backend: hatchling
- Package: `packages = ["substrate"]`
- Python requirement: `>=3.11`
- Key dependencies: pydantic, psycopg2-binary, anthropic, google-genai, groq, discord.py, fastapi
