# Campaign 22 — Governed Development Loop & Projection Factory Foundation

## Context

UMH is currently "Aware, Governed, Coordinated" — 21 campaigns of substrate runtimes composing intelligence, governance, execution, and learning. Campaign 22 is the FINAL substrate capability campaign. It transforms UMH into a "Governed Software Producer" — where a single command "Build feature X" flows through the complete pipeline: Intent → Architecture → Work Decomposition → Agent Assignment → Execution → Review → Approval → Merge → Learning → Capability Update, all inside governance.

After C22, the roadmap shifts from "Build UMH" to "Use UMH" — building projection MVPs (EOS, LOS, COS) through the system itself.

**What already exists:** ~80% of the required infrastructure is built across 20+ existing runtimes. The key subsystems — WorkPacketEngine (intent→packets), OrganismLoopEngine (8-step execution cycle), AgentFleetRuntime (agent assignment), ExecutionCoordinator (plan→queue→dispatch), AutonomousPRFactory (worktree→validate→commit→PR→merge), CompoundingEngine (outcome→capability promotion), GovernanceRuntime (authority hierarchy), MetaIDERuntime (inspect→plan→assign→execute→review→merge loop) — are all production-ready. C22 composes these into a single governed development pipeline.

---

## Implementation Plan

### Build Order

```
Wave 1 (parallel — no interdependency):
  C22.0  Dev Operations Runtime
  C22.1  Work Packet Factory Runtime  
  C22.2  Agent Development Runtime
  C22.3  Development Review Runtime
  C22.4  Capability Compounding Runtime

Wave 2 (depends on C22.1):
  C22.5  Projection Factory Runtime

Wave 3 (depends on all above):
  C22.6  Development Center Routes + cockpit mount

Wave 4:
  Acceptance tests
  canonical_types.py registration
```

All Wave 1 runtimes use lazy imports — no hard compile-time dependency between them. They can be built and tested independently.

---

### C22.0 — Development Operations Runtime

**File:** `substrate/organism/dev_ops_runtime.py` (~400 lines)
**Test:** `tests/test_c22_dev_ops_runtime.py` (~35 tests)

**Purpose:** Unified view of software development work. The "what is being built?" dashboard.

**Composes (all lazy @property with try/except):**
- `MetaIDERuntime` (substrate/organism/meta_ide_runtime.py) — existing development loop (inspect/plan/assign/execute/review/merge), DevelopmentPhase enum, plans/streams/reviews state
- `GovernedExecutionRuntime` (substrate/organism/governed_execution_runtime.py) — execution state, blockers, approvals
- `ExecutionFabricRuntime` (substrate/workstation/execution_fabric_runtime.py) — active executions, capacity, queue depth
- `AgentWorkforceRuntime` (substrate/workstation/agent_workforce_runtime.py) — agent health, idle/overloaded
- `SessionMachineRuntime` (substrate/workstation/session_machine_runtime.py) — session bindings, device utilization
- `MetaIdeContextRuntime` (substrate/workstation/meta_ide_context_runtime.py) — repo, branch, active files

**New types (inline):**
- `DevOpsPhase` enum: IDLE, PLANNING, IMPLEMENTING, REVIEWING, APPROVAL_PENDING, MERGING, LEARNING, DEGRADED
- `DevOpsSnapshot` dataclass: phase, health, current_build, active_agents, pending_reviews, pending_approvals, blocked_count, queue_depth, session_context, generated_at

**Key design decision:** DevOpsPhase is DERIVED, not a state machine. The `phase` property reads subsystems and deterministically classifies:
- MetaIDERuntime has active streams with EXECUTING phase? → IMPLEMENTING
- Pending reviews? → REVIEWING
- Pending approvals? → APPROVAL_PENDING
- Approved reviews awaiting merge? → MERGING
- Work packets in PLANNED status? → PLANNING
- Active learning extraction? → LEARNING
- Any subsystem degraded? → DEGRADED
- Otherwise → IDLE

**Methods:** `phase()`, `snapshot()`, `current_build()`, `what_ships_next()`, `blockers()`, `summary()`

**What's new:** ~5% new logic (phase derivation). Rest is composition.

---

### C22.1 — Work Packet Factory Runtime

**File:** `substrate/organism/work_packet_factory_runtime.py` (~550 lines)
**Test:** `tests/test_c22_work_packet_factory.py` (~45 tests)

**Purpose:** Convert goals into executable development packets. "Build EOS Dashboard" → Architecture + Backend + Frontend + Test + Review + Documentation packets.

**Composes (all lazy):**
- `WorkPacketEngine` (substrate/organism/work_packet_engine.py) — `decompose_intent_to_batch()`, `create_packet_from_intent()`
- `GovernanceRuntime` — risk classification for packets
- `TradeoffIntelligenceEngine` — "if we build X, what don't we build?"
- `TrajectoryIntelligenceRuntime` — goal forecasting for prioritization

**New types (inline):**
- `DevelopmentPacketType` enum: ARCHITECTURE, BACKEND, FRONTEND, TEST, REVIEW, DOCUMENTATION, DEPLOYMENT, INTEGRATION
- `DevelopmentDecomposition` dataclass: goal, packets, dependency_order, tradeoff_analysis, risk_summary, estimated_agent_types, generated_at

**What's genuinely new (~40%):** Development-specific decomposition templates. The existing `WorkPacketEngine._decomposition_steps()` has templates for `implementation`, `analysis`, `deployment`, `content_creation` — but NOT for full software development lifecycle. C22.1 adds:

```python
_DEVELOPMENT_TEMPLATES = {
    "software_development": [
        ("architecture", "Architecture Design"),
        ("backend", "Backend Implementation"),
        ("frontend", "Frontend Implementation"),
        ("testing", "Test Suite"),
        ("review", "Code Review"),
        ("documentation", "Documentation"),
    ],
    "feature_addition": [
        ("planning", "Feature Plan"),
        ("implementation", "Implementation"),
        ("testing", "Tests"),
        ("review", "Review"),
    ],
    "bug_fix": [
        ("analysis", "Root Cause Analysis"),
        ("implementation", "Fix"),
        ("testing", "Regression Tests"),
        ("verification", "Verification"),
    ],
    "refactor": [
        ("analysis", "Impact Analysis"),
        ("implementation", "Refactor"),
        ("testing", "Tests"),
        ("review", "Review"),
    ],
}
```

The factory wraps `WorkPacketEngine.decompose_intent_to_batch()` — does NOT recreate packet logic. It adds: development-type classification (deterministic keyword matching), template selection, tradeoff analysis wrapper, agent type estimation per packet.

**Methods:** `goal_to_development_packets(goal, constraints, packet_types)`, `classify_development_type(goal)`, `estimate_packet_risk(packet_type, goal)`, `tradeoff_preview(goal)`

---

### C22.2 — Agent Development Runtime

**File:** `substrate/organism/agent_dev_runtime.py` (~420 lines)
**Test:** `tests/test_c22_agent_dev_runtime.py` (~35 tests)

**Purpose:** Connect workforce to development packets. Who should do this? Who is overloaded? Who reviews? Who merges?

**Composes (all lazy):**
- `AgentWorkforceRuntime` (substrate/workstation/agent_workforce_runtime.py) — idle/overloaded agents
- `ExecutionCoordinator` (substrate/organism/execution_coordinator.py) — execution plans, queue, lifecycle
- `AgentFleetRuntime` (substrate/organism/agent_fleet_runtime.py) — `assign()`, `dispatch()`, capability scoring
- `DelegationReadinessRuntime` (substrate/organism/delegation_readiness_runtime.py) — delegation feasibility

**New types (inline):**
- `AssignmentStatus` enum: UNASSIGNED, ASSIGNED, IN_PROGRESS, REVIEWING, COMPLETED, BLOCKED
- `DevelopmentAssignment` dataclass: packet_id, agent_type, assignment_rationale, status, reviewer_agent, merge_authority, compute_node, assigned_at
- `DevelopmentProgress` dataclass: total_packets, assigned, in_progress, reviewing, completed, blocked, agents_involved, estimated_completion

**Methods:** `assign_development_work(packets)`, `development_progress()`, `who_should_review(packet_id)`, `who_is_overloaded()`, `who_is_idle()`, `summary()`

**What's new:** ~15% new logic (reviewer selection heuristic, progress aggregation). Rest delegates to existing runtimes.

---

### C22.3 — Development Review Runtime

**File:** `substrate/organism/dev_review_runtime.py` (~480 lines)
**Test:** `tests/test_c22_dev_review_runtime.py` (~40 tests)

**Purpose:** Governed review layer. Tests, architecture compliance, type compliance, dependency compliance, projection compliance, review status.

**Composes (all lazy):**
- `UnifiedApprovalRuntime` (substrate/workstation/unified_approval_runtime.py) — pending approvals
- `GovernanceRuntime` (substrate/organism/governance_runtime.py) — authority evaluation
- `ReviewPackageBuilder` (substrate/meta_ide/review_package_builder.py) — proof assembly
- `TrajectoryIntelligenceRuntime` — risk prediction
- `LearningExtractionRuntime` — lessons from past reviews

**New types (inline):**
- `ReviewVerdict` enum: READY, CHANGES_REQUIRED, BLOCKED, APPROVAL_PENDING
- `ComplianceCheckType` enum: TESTS, ARCHITECTURE, TYPE_COHERENCE, DEPENDENCY_DIRECTION, PROJECTION_BOUNDARY, INSTANCE_CONTEXT
- `ComplianceCheck` dataclass: check_type, passed, details, gate_script
- `DevelopmentReviewResult` dataclass: packet_id, verdict, compliance_checks, proof_package, governance_evaluation, risk_assessment, blocking_reasons, generated_at

**What's genuinely new (~30%):** The compliance check runner wrapping the 5 pre-commit gate scripts (`check_dependency_direction.py`, `check_type_divergence.py`, `check_projection_leak.py`, `check_instance_leak.py`, `check_cpu_gate.py`) into structured ComplianceCheck results. Uses `gated_subprocess_run()` from `substrate/execution/cpu_gate.py`.

**Methods:** `review_packet(packet_id)`, `compliance_status(packet_id)`, `pending_reviews()`, `review_history(limit)`, `summary()`

---

### C22.4 — Capability Compounding Runtime

**File:** `substrate/organism/capability_compounding_runtime.py` (~400 lines)
**Test:** `tests/test_c22_capability_compounding.py` (~35 tests)

**Purpose:** Operationalized learning. Feature → Pattern → Capability → Reusable Asset.

**Composes (all lazy):**
- `LearningExtractionRuntime` (substrate/organism/learning_extraction_runtime.py) — lessons
- `InstitutionalMemoryRuntime` (substrate/organism/institutional_memory_runtime.py) — knowledge lifecycle
- `CapabilityEvolutionEngine` (substrate/organism/capability_evolution_engine.py) — maturity tracking
- `OutcomePatternEngine` (substrate/organism/outcome_pattern_engine.py) — pattern detection
- `CompoundingEngine` (substrate/organism/compounding_engine.py) — 4-tier promotion pipeline

**New types (inline):**
- `CompoundingStage` enum: OUTCOME, LESSON, PATTERN, CAPABILITY, OPERATIONAL
- `CompoundingSnapshot` dataclass: total_outcomes, total_lessons, total_patterns, capabilities_evolved, pending_promotions, institutional_health, compounding_velocity, reusable_assets, generated_at

**What's new:** ~5% new logic. `feature_to_asset_pipeline(feature_id)` traces lineage across 5 subsystems. Everything else delegates.

**Methods:** `snapshot()`, `feature_to_asset_pipeline(feature_id)`, `pending_promotions()`, `institutional_health()`, `reusable_assets()`, `summary()`

---

### C22.5 — Projection Factory Runtime

**File:** `substrate/organism/projection_factory_runtime.py` (~500 lines)
**Test:** `tests/test_c22_projection_factory.py` (~40 tests)

**Purpose:** Given a projection definition (EOS/LOS/COS), generate: goal tree, work packets, development plan, capability map. No special EOS/LOS/COS logic — factory treats all projections identically.

**Composes (all lazy):**
- `ProjectionIntegrationRuntime` (substrate/organism/projection_integration_runtime.py) — existing projections, gaps, maturity
- `WorkPacketFactoryRuntime` (C22.1) — packet generation
- `GovernanceRuntime` — policy evaluation
- `TradeoffIntelligenceEngine` — displacement analysis

**New types (inline):**
- `ProjectionGoalType` enum: INFRASTRUCTURE, FEATURE, INTEGRATION, MIGRATION, CAPABILITY
- `ProjectionGoal` dataclass: goal_id, projection_id, goal_type, title, description, dependencies, priority, risk_class
- `ProjectionPlan` dataclass: projection_id, projection_name, goals, work_packets, capability_requirements, gap_analysis, estimated_complexity, generated_at

**What's genuinely new (~40%):** Goal tree generation from projection definition + gap analysis. Schema: `{id, name, goals: [{title, description, type}]}`. The factory's job is decomposition, not projection understanding.

**Methods:** `generate_projection_plan(projection_id, projection_definition)`, `list_projections()`, `projection_readiness(projection_id)`, `summary()`

---

### C22.6 — Development Center Routes

**File:** `transports/api/cockpit_dev_center_routes.py` (~200 lines)
**Test:** `tests/test_c22_dev_center_routes.py` (~20 tests)
**Mount in:** `transports/api/cockpit.py` (add `_mount_dev_center_router()` + call — ~7 lines)

**Pattern:** Same as `cockpit_runtime_surface_routes.py` — FastAPI APIRouter, lazy singleton init, `configure()` function.

**Endpoints (9):**
```
GET /dev-center/snapshot          → DevOpsRuntime.snapshot()
GET /dev-center/phase             → DevOpsRuntime.phase()
GET /dev-center/current-build     → DevOpsRuntime.current_build()
GET /dev-center/agents            → AgentDevRuntime.summary()
GET /dev-center/reviews           → DevReviewRuntime.pending_reviews()
GET /dev-center/approvals         → DevReviewRuntime.summary()
GET /dev-center/learning          → CapabilityCompoundingRuntime.snapshot()
GET /dev-center/compounding       → CapabilityCompoundingRuntime.pending_promotions()
GET /dev-center/projections       → ProjectionFactoryRuntime.list_projections()
```

---

### Type Registration

Add 7 new enums to `substrate/canonical_types.py`:
- `DevOpsPhase` → `substrate.organism.dev_ops_runtime`
- `DevelopmentPacketType` → `substrate.organism.work_packet_factory_runtime`
- `AssignmentStatus` → `substrate.organism.agent_dev_runtime`
- `ReviewVerdict` → `substrate.organism.dev_review_runtime`
- `ComplianceCheckType` → `substrate.organism.dev_review_runtime`
- `CompoundingStage` → `substrate.organism.capability_compounding_runtime`
- `ProjectionGoalType` → `substrate.organism.projection_factory_runtime`

---

### Acceptance Tests

**File:** `tests/test_c22_acceptance.py` (~15 tests)

**AT1 — Full Development Loop:**
WorkPacketFactory decomposes "Build user dashboard" → 5-6 packets → AgentDevRuntime assigns agents → DevReviewRuntime runs compliance → CapabilityCompoundingRuntime snapshot shows pipeline exists.

**AT2 — Capability Reuse (Compounding Proven):**
Run AT1 twice. Second run's WorkPacketFactory should produce packets with prior capability references. CompoundingEngine tracks the lineage.

**AT3 — Projection Factory (Universal):**
Define two projections with different names but same structure. Both produce identical plan shapes — no projection-specific code paths.

**AT4 — Work Resumes From Prior State:**
Create a projection plan, persist. Load from persistence. Verify state matches.

**AT5 — Voice-to-Development Queue:**
Simulate voice intent text → DevOpsRuntime.snapshot() shows PLANNING phase → WorkPacketFactory produces packets → packets appear in development queue.

---

### What NOT To Build / Modify

- Do NOT modify `WorkPacketEngine` — C22.1 wraps it
- Do NOT modify `ExecutionCoordinator` — C22.2 reads from it
- Do NOT modify `GovernanceRuntime` — C22.3 calls it
- Do NOT modify any learning runtimes — C22.4 composes them
- Do NOT modify `ProjectionIntegrationRuntime` — C22.5 reads from it
- Do NOT modify `MetaIDERuntime` — C22.0 composes it
- Do NOT modify `AutonomousPRFactory` — existing PR lifecycle is complete
- Do NOT modify `OrganismLoopEngine` — C22 is composition, not execution authority
- Do NOT add LLM calls — everything is deterministic
- Do NOT create nested directories — all files flat in `substrate/organism/`
- Do NOT create new abstract ports in `substrate/sockets/`

---

### Files Modified (2 only)

1. `substrate/canonical_types.py` — add 7 type registrations
2. `transports/api/cockpit.py` — add `_mount_dev_center_router()` block (~7 lines)

### Files Created (15)

| File | Est. Lines |
|------|-----------|
| `substrate/organism/dev_ops_runtime.py` | ~400 |
| `substrate/organism/work_packet_factory_runtime.py` | ~550 |
| `substrate/organism/agent_dev_runtime.py` | ~420 |
| `substrate/organism/dev_review_runtime.py` | ~480 |
| `substrate/organism/capability_compounding_runtime.py` | ~400 |
| `substrate/organism/projection_factory_runtime.py` | ~500 |
| `transports/api/cockpit_dev_center_routes.py` | ~200 |
| `tests/test_c22_dev_ops_runtime.py` | ~350 |
| `tests/test_c22_work_packet_factory.py` | ~450 |
| `tests/test_c22_agent_dev_runtime.py` | ~350 |
| `tests/test_c22_dev_review_runtime.py` | ~400 |
| `tests/test_c22_capability_compounding.py` | ~350 |
| `tests/test_c22_projection_factory.py` | ~400 |
| `tests/test_c22_dev_center_routes.py` | ~200 |
| `tests/test_c22_acceptance.py` | ~250 |

**Total: ~5,700 LOC (runtimes+routes+tests)**

---

### Verification

After all files created:
1. `python3 -m py_compile` every new .py file
2. `python3 -m pytest tests/test_c22_*.py -v` — all ~265 tests pass
3. `python3 scripts/check_type_divergence.py --all` — no new violations
4. `python3 scripts/check_dependency_direction.py --all` — no violations
5. `python3 scripts/check_projection_leak.py --all` — no projection names in substrate/
6. `python3 scripts/check_instance_leak.py --all` — no instance context leaks
7. Import check: `python3 -c "from substrate.organism.dev_ops_runtime import DevelopmentOperationsRuntime; print('C22.0 OK')"`
8. Repeat import check for all 6 runtimes
9. Cockpit mount: restart cockpit, verify `/api/umh/dev-center/snapshot` returns JSON
