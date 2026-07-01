# UMH Platform Specification v1.0

Established 2026-06-30 after C40B achieved PRODUCTION READY.
This document is the constitution of the execution platform.

Every future feature is measured against this specification.
If a proposal violates a contract, it either changes the specification
through an explicit versioned process, or adapts to the platform.

---

## Versioning Policy

- MAJOR: breaking contract change (new required fields, changed signatures,
  removed interfaces). Requires migration path + regression qualification.
- MINOR: additive change (new optional fields, new methods, new enum values).
  Must not break existing consumers.
- PATCH: internal implementation change. Contract surface unchanged.

Current version: **1.0.0**

Changes to this document require a versioned commit with rationale.
The diff IS the changelog.

---

## 1. Canonical Mutation Contract

Every state change in UMH routes through governed mutation.
No exceptions. No backdoors.

### Entry Point

```
governed_mutation(
    mutation_name: str,
    intent: str,
    execute_fn: Callable[[], tuple[str, bool]],
    source: str = "cockpit",
    metadata: dict | None = None,
    verification_fn: Callable[[], bool] | None = None,
    rollback_fn: Callable[[], bool] | None = None,
    require_approval: bool | None = None,
) -> MutationResponse
```

**Canonical location:** `transports/api/governed.py`

### Core Types

```
MutationRequest:
    mutation_name: str
    intent: str
    execute_fn: Callable[[], tuple[str, bool]]
    source: str
    metadata: dict | None
    risk_level: str | None
    blast_radius: str | None
    reversibility: str | None
    require_approval: bool | None
    verification_fn: Callable[[], bool] | None
    rollback_fn: Callable[[], bool] | None

MutationResponse:
    success: bool
    output: str
    envelope_id: str
    status: str
    awaiting_approval: bool
    rejected_reason: str
    envelope: ActionEnvelope | None
    .to_http_dict() -> dict
```

**Canonical location:** `substrate/organism/mutation_router.py`

### Registry

```
MutationSpec:
    name: str
    action_type: str
    risk_level: str
    reversibility: str
    allowed_modes: list[str]
    required_capabilities: list[str]
    verification_required: bool
    rollback_supported: bool
    blast_radius: str
    timeout_seconds: int
    max_retries: int
    require_approval: bool
    description: str

MutationRegistry:
    .register(spec: MutationSpec)
    .lookup(name: str) -> MutationSpec | None
    .is_registered(name: str) -> bool
    .all_specs() -> list[MutationSpec]
    .specs_by_risk(risk: str) -> list[MutationSpec]
    .specs_by_type(action_type: str) -> list[MutationSpec]
```

**Canonical location:** `substrate/organism/mutation_registry.py`

### Invariants

- execute_fn signature: `() -> tuple[str, bool]` (output, success)
- Every mutation gets an ActionEnvelope before execution
- Governance check runs before every execution
- Journal records every lifecycle phase
- Event spine emits for every state transition

### Breaking Changes

- Adding required fields to MutationRequest or MutationResponse
- Changing execute_fn signature
- Changing MutationResponse.to_http_dict() shape
- Removing MutationSpec fields

---

## 2. Governed Execution Contract

The 8-stage pipeline that every mutation traverses.

### Pipeline

```
Propose -> Governance Check -> Approve/Reject -> Execute
-> Verify -> Learn -> Journal -> Event
```

### Core Types

```
ActionEnvelope:
    intent: str
    action_type: ActionType
    source: str
    execute_fn: Callable
    envelope_id: str (auto-generated)
    risk_level: str
    blast_radius: BlastRadius
    reversibility: ReversibilityClass
    status: EnvelopeStatus
    result_output: str
    result_success: bool
    ...

ActionType: FILESYSTEM | CONTAINER | PROCESS | NETWORK | STATE |
    GRAPH | TEST | CLEANUP | INGESTION | DEPLOYMENT

EnvelopeStatus: PROPOSED | APPROVED | REJECTED | EXECUTING |
    COMPLETED | FAILED | ROLLED_BACK | VERIFIED | VERIFICATION_FAILED

ReversibilityClass: FULLY_REVERSIBLE | PARTIALLY_REVERSIBLE | IRREVERSIBLE

BlastRadius: LOCAL_FILE | LOCAL_RUNTIME | SINGLE_SERVICE |
    MULTI_SERVICE | CLUSTER_WIDE | EXTERNAL
```

**Canonical location:** `substrate/organism/action_envelope.py`

### Spine Interface

```
GovernedExecutionSpine:
    .submit(envelope: ActionEnvelope) -> ActionEnvelope
    .approve(envelope_id: str, approved_by: str = "operator") -> ActionEnvelope | None
    .reject(envelope_id: str, reason: str) -> ActionEnvelope | None
    .pending_envelopes(limit: int = 50) -> list[dict]
    .active_envelopes() -> list[dict]
    .completed_envelopes(limit: int = 50) -> list[dict]
    .envelope_lifecycle(envelope_id: str) -> list[dict]
```

**Canonical location:** `substrate/organism/governed_spine.py`

### Invariants

- submit() always returns an ActionEnvelope (never None, never raises)
- Governance check runs synchronously before execution
- Execution journal records every phase transition
- Event spine emits for every status change
- Pipeline order is fixed: governance -> execute -> verify -> learn

### Breaking Changes

- Changing submit() return type
- Adding required constructor arguments
- Changing ActionEnvelope required fields
- Altering pipeline stage order
- Changing EnvelopeStatus enum values

---

## 3. Event Contract

The single pub/sub backbone. Every subsystem communicates through events.

### Core Types

```
EventDomain: RUNTIME | GOVERNANCE | ADVISOR | WORKCELL | OBJECTIVE |
    EXECUTION | LEVERAGE | SUPERVISOR | FILESYSTEM | TMUX | DOCKER |
    PROJECTION | TRANSPORT | RECURSION | MEMORY | OBSERVABILITY |
    OPERATOR | WORKER

EventPriority: LOW | NORMAL | HIGH | CRITICAL

OrganismEvent:
    domain: EventDomain
    event_type: str
    source: str
    data: dict
    priority: EventPriority (default NORMAL)
    event_id: str (auto-generated)
    timestamp: float (auto-generated)
    correlation_id: str | None
    .to_dict() -> dict
```

**Canonical location:** `substrate/organism/event_spine.py`

### Spine Interface

```
EventSpine:
    .emit(domain, event_type, source, data, priority=NORMAL, correlation_id=None)
    .subscribe(subscriber_id: str, handler: Callable, domains: list | None = None)
    .unsubscribe(subscriber_id: str)
    .recent(limit: int = 50) -> list[OrganismEvent]
    .replay(subscriber_id: str, since_timestamp: float, handler: Callable)
    .snapshot() -> dict
    .recover() -> int
    .flush()
```

### Invariants

- emit() is synchronous and never raises
- Subscribers receive events in emission order
- Events are immutable after emission
- Event loss count must remain 0 under normal operation

### Breaking Changes

- Changing OrganismEvent field names or types
- Changing emit() signature
- Removing EventDomain values that existing subscribers filter on
- Changing to_dict() shape

---

## 4. Runtime Adapter Contract (Mesh)

Cross-device execution via the node mesh.

### HTTP Dispatch (VPS -> Mesh Server)

```
POST /dispatch
Request:  {node_id, capability, params, timeout}
Response: {ok, status, result_data, error, latency_ms}
```

### JSON-RPC (Mesh Server -> Node Client, over WebSocket)

```
Request:  {jsonrpc: "2.0", method: "capability.execute",
           params: {request_id, capability_name, params, timeout_seconds}, id}
Response: {jsonrpc: "2.0",
           result: {success, result_data, latency_ms, side_effects}, id}
```

### Adapter Interface (Node Client -> Adapter)

```
adapter.execute(capability_name: str, params: dict) -> dict
    Returns: {success: bool, stdout: str, stderr: str, exit_code: int, ...}
```

**Canonical locations:**
- Server: `transports/node_mesh/server.py`
- Client: `nodes/windows/umh_node/client.py`

### Invariants

- Dispatch is synchronous with timeout
- result_data is always a dict (never raw string)
- success field is always present in adapter response
- Timeout at any layer produces {ok: false, error: "timeout"}

### Breaking Changes

- Changing /dispatch request or response shape
- Changing JSON-RPC method name from "capability.execute"
- Changing result_data wrapping structure
- Altering the {success, result_data} contract at any boundary

---

## 5. Proof Contract

Evidence collection for operator verification.

### Entry Point

```
trigger_collection(
    target_url: str,
    pass_count: int = 3,
) -> dict[str, Any]
    Returns: {passes: list[PassEvidence.to_gate_format()], error?, collection_node, ...}
```

**Canonical location:** `substrate/meta_ide/browser_evidence_collector.py`

### Evidence Types

```
ViewportEvidence:
    viewport_name, width, height, browser_engine,
    browser_layer, network_layer, console_layer, log_layer

PassEvidence:
    pass_number, viewports: list[ViewportEvidence], timestamp,
    browser_check, network_check, console_check, log_check
    .to_gate_format() -> dict
```

### Invariants

- Collection always routes through mesh dispatch (primary) or SSH (fallback with warning)
- Executor must have `role: executor` in `infra/device_registry.json`
- Evidence is never synthetic in production (real browser, real DOM, real screenshots)
- Credentials flow through 1Password `op run` — never plaintext

### Breaking Changes

- Changing trigger_collection() return shape (especially `passes` key)
- Changing to_gate_format() structure
- Altering executor resolution logic

---

## 6. Qualification Contract

Organism qualification — the measurement of operational readiness.

### Operational Readiness Levels

| ORL | Name | Meaning |
|-----|------|---------|
| 1 | COMPONENTS_EXIST | Individual substrate components exist and compile |
| 2 | COMPONENTS_CONNECTED | Components can communicate and exchange data |
| 3 | CANONICAL_MUTATION_ENFORCED | All state changes route through governed mutation |
| 4 | STABLE_UNDER_LOAD | System maintains correctness under sustained operation |
| 5 | ADAPTIVE_LEARNING | Outcome learning loop improves behavior over time |
| 6 | AUTONOMOUS_COORDINATION | Multi-agent coordination without human intervention |
| 7 | SELF_REGULATING | System detects and corrects its own degradation |
| 8 | PRODUCTION_QUALIFIED | Full qualification at >= 95% confidence |

### Qualification Report

```
QualificationReport:
    orl_achieved: int
    orl_confidence: float
    predictive_accuracy: float
    properties: list[PropertyResult]
    drift: dict
    total_mutations: int
    total_duration_s: float
    hypothesis_result: str
    weakest_property: str
    recommendation: str
    convergence_status: str
    stopping_reason: str
    .to_dict() -> dict
```

### Entry Point

```
run_qualification() -> QualificationReport
```

**Canonical location:** `substrate/organism/qualification_harness.py`

### 10 Qualification Properties

| # | Property | Gates ORL |
|---|----------|-----------|
| 1 | Mutation Integrity | Yes |
| 2 | Operational Coverage | Yes |
| 3 | State Consistency | Yes |
| 4 | Adaptive Intelligence | Yes |
| 5 | Operational Entropy | Yes |
| 6 | Autonomous Coordination | Yes |
| 7 | Meta-Orchestration | Yes |
| 8 | Recovery & Homeostasis | Yes |
| 9 | Self-Regulation | Yes |
| 10 | Predictive Accuracy | No (informational) |

### Invariants

- Properties converge via rolling window (50 items, <10% stdev, 3 consecutive)
- ORL is never assigned without evidence — always computed from property convergence
- Qualification is additive — it loads historical mutation data
- PA of 0.0 with no predictions made = "not evaluated", not regression

### Breaking Changes

- Changing ORL level definitions or values
- Changing QualificationReport fields
- Altering property numbering or gating rules
- Changing run_qualification() signature

---

## 7. Organism Contract

The daemon that wires all substrate subsystems together.

### Daemon Interface

```
OrganismDaemon:
    .event_spine -> EventSpine
    .governed_spine -> GovernedExecutionSpine
    .mutation_registry -> MutationRegistry
    .execution_journal -> ExecutionJournal
    .outcome_learning -> OutcomeLearningLoop
    .advisor -> AdvisorWorkcell
    .store -> MutationRegistry
    .approval_store -> ApprovalStore
```

**Canonical location:** `substrate/organism/daemon.py`

### Journal Interface

```
ExecutionJournal:
    .record(envelope_id: str, phase: JournalPhase, source: str, metadata: dict)
    .entries_for(envelope_id: str) -> list[JournalEntry]
    .entries_by_phase(phase, limit=50) -> list[JournalEntry]
    .recent(limit=50) -> list[JournalEntry]
    .execution_lifecycle(envelope_id: str) -> list[dict]
```

### Learning Interface

```
OutcomeLearningLoop:
    .record_outcome(outcome: OutcomeRecord) -> OutcomeEvaluation
```

**Canonical locations:**
- Journal: `substrate/organism/execution_journal.py`
- Learning: `substrate/organism/outcome_learning.py`

### Invariants

- OrganismDaemon is a singleton coordinator — it owns all subsystem lifecycles
- All properties are lazy-initialized
- Journal is append-only
- Learning loop runs after every completed execution

### Breaking Changes

- Removing or renaming daemon properties
- Changing ExecutionJournal.record() or entries_for() signatures
- Changing OutcomeRecord structure

---

## 8. Predictive Self-Model Contract

The organism's ability to predict its own behavior.

```
PredictiveSelfModel:
    .predict(mutation_name, action_type, risk_level) -> dict[str, PredictionResult]
    .record_actual(mutation_name, action_type, risk_level, success, duration_ms, retry_count)
    .record_from_mutation(record) -> dict[str, PredictionResult]
    .prediction_accuracy() -> ConfidenceEstimate
    .calibration_score() -> float
    .per_metric_accuracy() -> dict
    .worst_predictors(n=5) -> list[tuple[str, float]]

PredictionResult:
    predicted: float
    lower: float
    upper: float
    confidence: float
    metric: str
    feature_key: str
    sample_size: int
    is_cold_start: bool
    .contains(actual: float) -> bool
```

**Canonical location:** `substrate/organism/self_model_predictor.py`

### Invariants

- Predictions are statistical (CI-based), not deterministic
- Cold-start predictions are flagged via is_cold_start
- Accuracy is measured as 1.0 - MAPE
- Model improves with each recorded actual outcome

### Breaking Changes

- Changing predict() or record_actual() signatures
- Altering PredictionResult fields
- Changing how prediction_accuracy() is computed

---

## 9. Type Contract

Canonical type definitions. No parallel type systems.

### Key Types

```
SignalEnvelope: source, content, channel_id, guild_id, user_id, urgency, ...
RiskClass: BENIGN | REVERSIBLE_READ | REVERSIBLE_WRITE | IRREVERSIBLE_WRITE | DESTRUCTIVE
GovernanceVerdict: decision, risk_class, reasoning, constraints, ...
ExecutionResult: success, output, trace_id, ...
AdapterResponse: success, content, adapter_name, ...
```

**Canonical locations:**
- Domain types: `substrate/types.py`
- Type registry: `substrate/canonical_types.py` (1278 type->module mappings)

### Enforcement

Pre-commit hook `scripts/check_type_divergence.py` blocks new parallel type
definitions. All new types must be registered in `canonical_types.py`.

### Invariants

- One canonical location per type — never duplicated
- Pre-commit hook enforces registration
- Renaming a type requires updating all consumers in the same commit

---

## 10. Runtime SLOs

Established by C40B. These are the minimum targets for production operation.

| # | SLO | Target | C40B Baseline |
|---|-----|--------|---------------|
| 1 | mesh_reliability | >= 99% | 100.0% |
| 2 | session_availability | >= 95% | 100.0% |
| 3 | dispatch_success_rate | >= 95% | 100.0% |
| 4 | playwright_availability | >= 95% | 100.0% |
| 5 | chrome_startup_rate | >= 95% | 100.0% |
| 6 | recovery_rate | >= 80% | 100.0% |
| 7 | adapter_failure_rate | < 5% | 0.0% |
| 8 | avg_latency_ms | < 5000ms | 1590ms |
| 9 | p95_latency_ms | < 10000ms | 4069ms |
| 10 | event_loss | 0 | 0 |
| 11 | proof_completeness | 100% | 100.0% |

### Invariants

- SLOs are measured continuously during qualification runs
- All 11 must pass simultaneously for Runtime dimension PASS
- Latency targets account for cross-device mesh dispatch over Tailscale
- Event loss tolerance is zero — no events may be dropped

---

## 11. Qualification Dimensions

Four independent dimensions. Never collapsed into a single score.

| Dimension | What it measures | Pass criteria |
|-----------|-----------------|---------------|
| Organism | ORL, confidence, PA, governance, learning | ORL >= 8, confidence >= 0.95 |
| Runtime | All 11 SLOs | All targets met simultaneously |
| Projection | Event convergence, cross-surface equivalence, proof completeness | 0 event loss, 100% equivalence, 100% proof |
| Operator | Scenario success, evidence quality, workflow coverage | >= 95% success, 0 synthetic, >= 25 scenarios |

---

## 12. Production Readiness Gate

All 8 checks must pass for PRODUCTION READY verdict.

| # | Check | Requirement |
|---|-------|-------------|
| 1 | operator_all_workflows | 25/25 operator scenarios pass |
| 2 | no_synthetic_evidence | 0 synthetic evidence files |
| 3 | recovery_demonstrated | 10 injected failures recovered |
| 4 | computer_use_stable | 100+ operator executions without crash |
| 5 | browser_stable | Chrome + Playwright >= 95% availability |
| 6 | proof_chain_complete | Every action traceable intent -> proof |
| 7 | qualification_stable | ORL-8 preserved through stress |
| 8 | runtime_slos_met | All 11 SLO targets met |

---

## 13. Extension Points

New capabilities extend the platform through these interfaces:

1. **New mutation types** — register via `MutationRegistry.register(MutationSpec(...))`
2. **New event domains** — add to EventDomain enum (minor version bump)
3. **New adapters** — implement `adapter.execute(capability_name, params) -> dict`
4. **New qualification properties** — add to QualificationHarness (non-gating by default)
5. **New node types** — register in `infra/device_registry.json`
6. **New projections** — register via `substrate/sockets/projection_port.py`

### Extension Rules

- Extensions must not modify existing contract signatures
- New enum values are additive only (minor version)
- New required fields on existing types require major version
- All extensions must pass regression qualification before merge

---

## 14. Architecture Invariants

These hold across the entire codebase. Pre-commit hooks enforce them.

1. **Dependency direction**: substrate <- adapters <- transports <- projections (one-way down)
2. **No projection leak**: substrate/ never references EOS/CreatorOS/LyfeOS by name
3. **No instance leak**: substrate/ never contains user/org/device-specific values
4. **Type coherence**: no parallel type definitions (enforced by check_type_divergence.py)
5. **CPU gate**: no raw subprocess calls in gated directories (enforced by check_cpu_gate.py)
6. **Credential injection**: no plaintext credentials (enforced by check_credential_injection.py)
7. **File size**: no Python file over 3000 lines
8. **Deterministic first**: every LLM call has a deterministic fallback
9. **Observable by default**: every execution path emits enough information to
   reconstruct what happened without relying on logs external to the platform

---

## 15. Compatibility Policy

### API Classification

- **Public API**: governed_mutation(), EventSpine.emit/subscribe, MutationRegistry,
  OrganismDaemon properties, trigger_collection(). Backward-compatible across minor versions.
- **Internal API**: GovernedExecutionSpine internals, qualification property implementations,
  adapter wiring. May change in minor versions with migration notes.
- **Experimental API**: prefixed with `_experimental_` or documented as experimental.
  No stability guarantees. Must not be used by production projections.

### Guarantees

- **Backward compatibility**: public API consumers written for v1.x work on v1.y (y > x)
  without modification. Field additions are optional. New enum values are additive.
- **Forward compatibility**: not guaranteed. v1.x consumers should not assume v1.y features.
- **Deprecation policy**: deprecated APIs are annotated with `@deprecated(version, removal)`,
  continue to function for at least 2 minor versions, and emit a warning on use.
- **Migration windows**: breaking changes (major version) include a migration guide
  and a qualification run verifying the migration path.

---

## 16. Failure Model

Every subsystem classifies failures using this taxonomy.

| Failure Class | Meaning | Recovery |
|---------------|---------|----------|
| EXPECTED | Governed rejection, approval required, risk threshold | None — working as designed |
| TRANSIENT | Network timeout, mesh disconnect, temporary unavailability | Automatic retry with backoff |
| RECOVERABLE | Adapter failure, browser crash, session loss | Recovery within 30s (SLO target) |
| PERMANENT | Missing capability, invalid mutation spec, schema violation | Requires code change |
| GOVERNANCE | Risk too high, blast radius exceeded, approval denied | Operator decision |
| INFRASTRUCTURE | Node offline, Docker down, disk full, CPU throttled | Operational intervention |
| VERIFICATION | Post-execution verification failed | Rollback if supported |
| QUALIFICATION | ORL regression, SLO breach, property divergence | Qualification campaign |
| PREDICTION | Self-model prediction outside CI, calibration drift | Model retraining |

### Invariants

- Every caught exception maps to exactly one failure class
- No silent failures — every failure emits an event with classification
- Transient failures retry automatically; permanent failures surface immediately
- Governance failures are never retried without operator action

---

## 17. State Model

UMH models reality through distinct state categories.

| State | Meaning | Source |
|-------|---------|--------|
| Desired | What the operator wants | Mutation intent |
| Observed | What the platform sees now | Runtime measurement |
| Actual | What exists in the real system | Execution result |
| Projected | What surfaces show | Cockpit, CLI, API |
| Historical | What was true at time T | Journal, event log |
| Predicted | What the self-model expects | PredictiveSelfModel |
| Verified | What evidence confirms | Proof contract |

### Invariants

- Desired -> Actual gap drives execution
- Actual -> Projected gap drives rendering
- Predicted -> Actual gap drives learning
- Historical state is immutable and append-only
- Verified state requires real evidence (never synthetic in production)

---

## 18. Time Model

Temporal concepts used across the platform.

| Temporal Mode | Meaning | Example |
|---------------|---------|---------|
| Historical | What happened | Journal entries, event log |
| Present | What is happening now | Active envelopes, SLO measurements |
| Planned | What is queued | Pending mutations, approval queue |
| Scheduled | What will happen at time T | Autonomous cadence, maintenance loop |
| Predicted | What the model expects | Self-model forecasts |
| Simulated | What-if analysis | Dry-run mutations (dry_run_only mode) |

### Invariants

- All timestamps are Unix epoch floats (time.time())
- Historical records are immutable
- Scheduled actions execute through governed mutation (never bypass)
- Simulated results are always marked — never stored as actual

---

## 19. Identity Model

Every actor in the system has a canonical identity.

| Identity Type | Meaning | Resolution |
|---------------|---------|------------|
| Human | Operator/founder | UMH_USER_ID from BIS |
| AI Agent | Workcell agent (advisor, executor, etc.) | WorkcellRole enum |
| Service | Running service (os-discord, os-operator) | Container name |
| Daemon | OrganismDaemon, autonomous cadence | Process identity |
| Runtime | Execution context (qualification, campaign) | Source field in events |
| Node | Physical/virtual device | infra/device_registry.json |
| Organization | Tenant boundary | UMH_ORG_ID from BIS |

### Invariants

- Every event has a `source` field identifying the actor
- Every mutation has a `source` field (cockpit, cli, python, campaign, etc.)
- Node identities come from device_registry.json — never hardcoded
- Human/org identities come from BIS at runtime — never in substrate/

---

## 20. Capability Model

Capabilities are the unit of platform value. Mutations are how capabilities execute.

```
Capability
  ├── owns: list[MutationSpec]
  ├── requires: list[Capability]  (dependencies)
  ├── surfaces: list[str]         (cockpit, cli, api, etc.)
  └── qualification: QualificationReport
```

### Lifecycle

```
Define capability -> Register mutations -> Implement execute_fn
-> Wire surfaces -> Qualify -> Ship -> Regression guard
```

### Invariants

- Every mutation belongs to exactly one capability
- Capabilities are registered in MutationRegistry via MutationSpec
- New capabilities extend the platform through extension points (Section 13)
- Capability removal requires deprecation window (Section 15)
- Capabilities are qualified independently — one capability's failure
  does not invalidate another's qualification

### Future: Capability Registry

When capability count exceeds what MutationRegistry alone can organize,
a CapabilityRegistry will wrap MutationRegistry to provide:
- Capability-level qualification tracking
- Cross-capability dependency resolution
- Capability-scoped SLO measurement
- Capability lifecycle management (experimental -> stable -> deprecated)

This is a minor version extension — MutationRegistry interface is preserved.

---

## 21. Runtime SLO Categories

SLOs organized by operational concern (same 11 metrics as Section 10).

### Availability

| SLO | Target | C40B Baseline |
|-----|--------|---------------|
| mesh_reliability | >= 99% | 100.0% |
| session_availability | >= 95% | 100.0% |
| playwright_availability | >= 95% | 100.0% |
| chrome_startup_rate | >= 95% | 100.0% |

### Latency

| SLO | Target | C40B Baseline |
|-----|--------|---------------|
| avg_latency_ms | < 5000ms | 1590ms |
| p95_latency_ms | < 10000ms | 4069ms |

### Correctness

| SLO | Target | C40B Baseline |
|-----|--------|---------------|
| dispatch_success_rate | >= 95% | 100.0% |
| event_loss | 0 | 0 |

### Recovery

| SLO | Target | C40B Baseline |
|-----|--------|---------------|
| recovery_rate | >= 80% | 100.0% |
| adapter_failure_rate | < 5% | 0.0% |

### Evidence

| SLO | Target | C40B Baseline |
|-----|--------|---------------|
| proof_completeness | 100% | 100.0% |

---

## 22. Qualification Artifact Schema

Every qualification run produces artifacts with these fields.

```
QualificationArtifact:
    qualified_until: str          # ISO timestamp — validity window
    qualification_version: str    # PLATFORM_SPEC version tested against
    platform_version: str         # git SHA of the qualified commit
    evidence_hash: str            # SHA-256 of all evidence files
    qualification_hash: str       # SHA-256 of the qualification report
    artifact_hash: str            # SHA-256 of the entire artifact bundle
    dimensions: dict              # 4-dim verdict snapshot
    slo_scorecard: dict           # 11 SLO values at qualification time
    orl: int                      # ORL level achieved
    confidence: float             # ORL confidence
```

### Invariants

- Qualification artifacts are immutable after generation
- Hashes enable reproducibility verification
- qualified_until defines the validity window (requalify after expiry or
  after meaningful code changes, whichever comes first)
- Platform version ties qualification to a specific commit

---

## Certification History

| Campaign | ORL | Confidence | PA | Mutations | Achievement |
|----------|-----|------------|-----|-----------|-------------|
| C35 | 8 | 95.8% | -- | 180 | Organism qualified |
| C36 | 8 | 95.8% | -- | 200 | Adaptive qualification |
| C37 | 8 | 95.8% | 66.9% | 220 | Predictive self-model |
| C38 | 8 | 95.8% | 83.8% | 250 | Qualification optimization |
| C39 | 8 | 95.0% | 64.3% | 120 | Live gap-closure |
| C40A | 8 | 95.3% | 65.6% | 550 | Runtime convergence |
| C40B | 8 | 95.3% | N/E | 310 | Runtime embodiment — PRODUCTION READY |
