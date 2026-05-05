# MVP Scope Definition — Phase 75A

> Generated: 2026-05-02

---

## MVP Definition

A governed, stateful UMH prototype that:
1. Creates/loads a user instance (identity + org context)
2. Accepts a signal/input through the control plane
3. Routes through the 9-stage run loop
4. Uses the intelligence kernel for interpretation/decision support
5. Applies governance policy before execution
6. Produces an execution directive
7. Routes directive through the single execution spine
8. Executes through adapters (LLM, simulated, or real)
9. Writes results/outcomes through memory
10. Produces audit/observability records

---

## MVP Components

### 1. User Instance — CREATE/LOAD

**Existing modules to use**:
- `umh.control.identity` — Identity, IdentityStore
- `umh.workstation.business` — BusinessInstanceContext
- `umh.workstation.profile` — Workstation profile

**Missing**:
- Persistent identity store (currently in-memory dict)
- User instance bootstrap (create org + default identity on first use)

**Deferred**: Multi-user, Firebase auth, RBAC

**Acceptance criteria**:
- `POST /identity` creates a new identity with scoped permissions
- Identity persists across restarts (Neon or file-backed)
- `GET /identity/{id}` returns the active identity

### 2. Signal/Input Acceptance — CONTROL PLANE

**Existing modules to use**:
- `umh.control.api` — FastAPI endpoints (`POST /run`, `POST /execute`)
- `umh.gateway.entry` — `translate_and_run()`, `UMHInput`, `UMHOutput`

**Missing**:
- Input validation (schema enforcement on UMHInput)
- Rate limiting stub

**Deferred**: WebSocket streaming, SSE, batch endpoints

**Acceptance criteria**:
- `POST /run` accepts `{"input": "...", "source": "user"}` and returns `UMHOutput`
- Invalid input returns 422 with descriptive error
- All requests are identity-authenticated

### 3. 9-Stage Run Loop

**Existing modules to use**:
- `umh.run.run()` — full 9-stage pipeline already implemented
  1. `umh.signal.ingest.classify_input()` — signal classification
  2. `umh.intent.compiler.compile_intent()` — intent compilation
  3. `umh.world.model.WorldModel` — world model read/update
  4. `umh.goals.state.GoalRegistry` — goal selection
  5. Context composition (inline in run.py)
  6. `umh.capability.router.route_to_capability()` — capability routing
  7. `umh.governance.authority.check_governance()` — governance gate
  8. Capability execution (via registry)
  9. `umh.feedback.loop.record_outcome()` — outcome recording

**Missing**:
- World model persistence (reads from memory, doesn't persist updates)
- Strategy selection integration (goals.state is present but thin)

**Deferred**: LLM-enhanced interpretation, multi-step planning, parallel execution

**Acceptance criteria**:
- `run("What should I focus on today?")` returns a RunResult with all 9 stages traced
- RunTrace contains timing for every stage
- Governance blocks high-risk operations with ANALYZE authority level

### 4. Intelligence Kernel Integration (Optional Enhancement)

**Existing modules to use**:
- `umh.runtime.advisor` — aggregates intelligence signals
- `umh.runtime.regime` — regime classification
- `umh.runtime.weighted_decision` — decision scoring
- `umh.runtime.pattern_matching` — pattern recognition

**Missing**:
- Clean integration point between run loop and runtime intelligence
- Decision enrichment hook in run.py stage 4

**Deferred**: Full regime-aware planning, adaptive learning loop

**Acceptance criteria**:
- Intelligence kernel can be enabled/disabled via config flag
- When enabled, decision stage is enriched with regime context and pattern signals
- When disabled, run loop operates purely on deterministic intent→capability path

### 5. Governance Policy

**Existing modules to use**:
- `umh.governance.authority` — `check_governance()` with AuthorityLevel
- `umh.governance.governor` — ImprovementGovernor (controlled self-modification)
- `umh.execution.approval` — ApprovalStore

**Missing**:
- Policy configuration file (which operations require which authority level)
- Audit log persistence for governance decisions

**Deferred**: Multi-approver workflows, escalation chains

**Acceptance criteria**:
- Operations classified as EXECUTE or COMMIT are blocked without sufficient authority
- Blocked operations create approval requests in the approval store
- All governance decisions appear in RunTrace

### 6. Execution Directive

**Existing modules to use**:
- `umh.execution.contract` — ExecutionRequest, ExecutionResult, ExecutionClass
- `umh.execution.engine.execute()` — single canonical entry point

**Missing**: Nothing — this is fully implemented.

**Deferred**: Parallel execution, execution retry policies

**Acceptance criteria**:
- Every run produces an ExecutionRequest with class, constraints, and context
- execute() returns ExecutionResult with status, output, and timing

### 7. Single Execution Spine

**Existing modules to use**:
- `umh.execution.engine` — execute(), lightweight_execute()
- `umh.execution.stages` — typed execution stages
- `umh.execution.pipeline` — execution pipeline
- `umh.execution.interfaces` — backend + observer injection points

**Missing**:
- Default backend registration (currently requires manual set_execution_backend())
- Backend auto-discovery from adapters

**Deferred**: Distributed execution, execution branching

**Acceptance criteria**:
- All execution flows through execute() — no bypass paths
- Backend is auto-discovered from registered adapters
- Pipeline stages fire in order with observability

### 8. Adapter Execution

**Existing modules to use**:
- `umh.adapters.llm` — LLM adapter protocol
- `umh.adapters.null` — Null adapter (no-op for testing)
- `umh.adapters.stubs` — Stub adapters for standalone
- `umh.adapters.registry` — AdapterRegistry
- `umh.adapters.bridge` — Platform adapter discovery

**Missing**:
- Simulated adapter for MVP demo (returns canned responses for known intents)
- Adapter health check integration

**Deferred**: Browser adapter wiring, voice adapter, computer use

**Acceptance criteria**:
- LLM adapter routes to configured LLM provider (Gemini, Anthropic, Ollama)
- Null adapter allows full run loop to execute without any external calls
- Adapter failures are caught and recorded as FAILURE outcomes

### 9. Memory / Result Writing

**Existing modules to use**:
- `umh.memory.storage` — get_storage(), StorageBackend
- `umh.memory.persistent_store` — PersistentStore
- `umh.feedback.loop.record_outcome()` — outcome recording
- `umh.storage.adapters.neon` — Neon persistence

**Missing**:
- Outcome aggregation (count successes/failures per capability)
- Memory cleanup/retention policy

**Deferred**: Semantic search over outcomes, RLHF pipeline

**Acceptance criteria**:
- Every run writes an outcome record via record_outcome()
- Outcomes are retrievable by run_id
- Storage backend is configurable (Neon for prod, InMemory for tests)

### 10. Audit / Observability

**Existing modules to use**:
- `umh.run.RunTrace` — per-run trace with stage timings
- `umh.events.stream` — event emission
- `umh.execution.observability` — execution observer
- `umh.execution.metrics` — execution metrics
- `umh.decision.trace` — decision audit trail

**Missing**:
- Trace persistence (currently returned in response but not stored)
- Trace query endpoint in control plane

**Deferred**: OpenTelemetry export, dashboard, alerting

**Acceptance criteria**:
- Every run produces a RunTrace with all 9 stages
- Traces are persisted and queryable via `GET /traces/{run_id}`
- Decision trace captures the reasoning path (goal → strategy → capability)

---

## What is NOT in the MVP

| Category | Deferred Items |
|----------|---------------|
| Distribution | No packaging, no marketplace |
| Onboarding | No self-service onboarding flow |
| Multi-user | Single identity for MVP, no RBAC |
| Learning loop | Outcomes recorded but no automatic weight evolution |
| Distributed | No node federation, no cell distribution |
| Full intelligence | Regime, patterns, half-life available but optional |
| Browser/voice execution | Adapters exist but not wired |
| UI | No frontend — API + CLI only |
| Billing | No Stripe |

---

## MVP Module Inventory (126 MVP_CORE)

### Critical Path (used in every run)
```
umh/__init__.py          umh/run.py              umh/__main__.py
umh/core/clock.py        umh/core/config.py      umh/core/logging_config.py
umh/signal/ingest.py     umh/signal/types.py     umh/signal/router.py
umh/intent/compiler.py
umh/world/model.py
umh/goals/state.py
umh/context/builder.py   umh/context/types.py
umh/capability/registry.py  umh/capability/router.py
umh/governance/authority.py
umh/execution/engine.py  umh/execution/contract.py  umh/execution/interfaces.py
umh/feedback/loop.py
umh/memory/storage.py
umh/storage/backend.py   umh/storage/adapters/neon.py
umh/events/stream.py
umh/decision/trace.py
umh/gateway/entry.py
umh/protocols/*.py       (all 14 protocol definitions)
```

### Control Surface
```
umh/control/api.py       umh/control/cli.py      umh/control/identity.py
```

### Adapters (minimum set)
```
umh/adapters/base.py     umh/adapters/contracts.py
umh/adapters/registry.py umh/adapters/bridge.py
umh/adapters/llm.py      umh/adapters/null.py    umh/adapters/stubs.py
```

---

## Build Sequence

1. **Verify run loop** — `umh.run.run()` executes end-to-end with null adapter
2. **Persist identity** — add Neon-backed identity store
3. **Wire control plane** — ensure POST /run calls translate_and_run → run()
4. **Register default backend** — auto-discover LLM adapter as execution backend
5. **Persist traces** — store RunTrace in Neon, add GET /traces endpoint
6. **Persist world model** — add save/load for world model entries
7. **Wire governance audit** — log governance decisions to event stream
8. **Intelligence integration** — add optional enrichment hook in stage 4
9. **End-to-end test** — full request through control plane to execution to memory
10. **Demo path** — simulated adapter that shows the loop without LLM calls
