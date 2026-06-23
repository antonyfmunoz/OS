# Campaign 22 — Software Production Organism

## Context

UMH is currently "Aware, Governed, Coordinated" — 21 campaigns of substrate runtimes composing intelligence, governance, execution, and learning. Campaign 22 is the final major MVP substrate capability campaign before shifting primary effort from building UMH to using UMH to build projections. It transforms UMH into a **Governed Software Producer** — not by creating a development-specific workflow, but by making software production a **capability** the organism exercises through the same governed loop as any other work.

The critical correction from the original plan: development is not a special mode. It's one capability. Whether the target is UMH itself, an EOS projection, a client SaaS product, a landing page, or an internal tool — the pipeline is identical. The target is a parameter, not a code path.

After C22, UMH can build itself and build its projections through the same governed loop. The roadmap shifts from "Build UMH" to "Use UMH." Future substrate campaigns (deeper world-modeling, agent-native source control, richer simulation) may still happen — but C22 closes the MVP substrate capability set.

**What already exists:** ~80% of the required infrastructure is built across 20+ existing runtimes:
- `WorkPacketEngine` (intent→packets, 868 lines)
- `OrganismLoopEngine` (8-step execution cycle, 498 lines)
- `AgentFleetRuntime` (agent assignment + dispatch, 589 lines)
- `ExecutionCoordinator` (plan→queue→dispatch, 1179 lines)
- `AutonomousPRFactory` (worktree→validate→commit→PR→merge, 866 lines)
- `CompoundingEngine` (outcome→capability promotion, 457 lines)
- `GovernanceRuntime` (authority hierarchy + conflict arbitration, 687 lines)
- `MetaIDERuntime` (inspect→plan→assign→execute→review→merge, 538 lines)
- `ReviewPackageBuilder` (deterministic proof assembly, 182 lines)
- `DevelopmentSessionBridge` (coding agent governance observer, 354 lines)

C22 composes these into a single governed software production organism.

---

## Architectural Principles (from synthesis corrections)

1. **Development = one capability, not a workflow.** The organism produces software the same way it does any work — through intent→reality→packets→governance→execution→memory. No special "development mode."

2. **Target-agnostic production.** UMH, EOS, LOS, COS, client SaaS, websites, internal tools — same pipeline. The target is a parameter to the factory.

3. **World-class by default.** "Build X" automatically includes architecture, testing, security, observability, CI/CD, deployment, monitoring, recovery. The user never has to remember.

4. **Assisted build = delegated build.** User coding and agent coding are the same loop. The only difference is execution authority, not workflow.

5. **Agent hierarchy = org hierarchy.** Director → Lead → IC, nested recursively. Not 50 flat agents.

6. **Multi-project simultaneous production.** Project A, B, C building concurrently while operator works elsewhere. Production is organism work, not IDE-bound.

7. **Organizational lineage, not just code lineage.** Intent → Decision → Requirement → WorkPacket → Code → Review → Approval → Deployment → Outcome → Learning → Capability — all linked. GitHub tracks one layer. UMH tracks the full chain.

8. **Meta IDE = substrate, not panel.** Voice, Right Rail, Operations Center, Approvals, agent workforce — all can trigger production. Work continues while operator is elsewhere.

9. **Completion is outcome-based, not task-based.** A production request is not complete when code is generated. It is complete only when the desired end state is verified by proof: tests, gates, preview, logs, review package, and governance approval. If proof fails, the system loops again. If progress is unsafe, unclear, or blocked, governance escalates. Production loops until the requested end state is achieved or governance blocks progress.

---

## Implementation Plan

### Build Order

```
Wave 1 (parallel — no interdependency):
  C22.0  Production Operations Runtime
  C22.1  Production Planning Runtime
  C22.2  Production Workforce Runtime
  C22.3  Production Review Runtime
  C22.4  Capability Compounding Runtime

Wave 2 (depends on C22.1):
  C22.5  Product Factory Runtime
  C22.6  Source Truth Runtime

Wave 3 (depends on all above):
  C22.7  Production Surface Routes + cockpit mount

Wave 4:
  Acceptance tests
  canonical_types.py registration
```

All Wave 1 runtimes use lazy imports — no hard compile-time dependency between them.

---

### C22.0 — Production Operations Runtime

**File:** `substrate/organism/production_ops_runtime.py` (~450 lines)
**Test:** `tests/test_c22_production_ops_runtime.py` (~40 tests)

**Purpose:** Unified view of ALL software production work. Not development-specific — answers "what is being produced?" across all targets (UMH, projections, client products, internal tools).

**Composes (all lazy @property with try/except):**
- `MetaIDERuntime` (substrate/organism/meta_ide_runtime.py) — existing development loop skeleton
- `GovernedExecutionRuntime` (substrate/organism/governed_execution_runtime.py) — execution state, blockers
- `ExecutionFabricRuntime` (substrate/workstation/execution_fabric_runtime.py) — active executions, capacity
- `AgentWorkforceRuntime` (substrate/workstation/agent_workforce_runtime.py) — agent health
- `SessionMachineRuntime` (substrate/workstation/session_machine_runtime.py) — session bindings
- `MetaIdeContextRuntime` (substrate/workstation/meta_ide_context_runtime.py) — repo, branch, active files

**New types (inline):**
```python
class ProductionPhase(str, Enum):
    IDLE = "idle"
    PLANNING = "planning"
    PRODUCING = "producing"        # not "implementing" — covers all production
    REVIEWING = "reviewing"
    APPROVAL_PENDING = "approval_pending"
    SHIPPING = "shipping"          # not "merging" — covers deploy/merge/publish
    LEARNING = "learning"
    DEGRADED = "degraded"

class ProductionTarget(str, Enum):
    SUBSTRATE = "substrate"        # UMH itself
    PROJECTION = "projection"     # EOS, LOS, COS
    CLIENT_PRODUCT = "client_product"
    INTERNAL_TOOL = "internal_tool"
    WEBSITE = "website"
    AUTOMATION = "automation"

@dataclass
class ProductionSnapshot:
    phase: str
    health: str
    active_productions: list[dict[str, Any]]  # target + packets + status
    workforce: dict[str, Any]                 # agent health summary
    pending_reviews: int
    pending_approvals: int
    blocked_count: int
    queue_depth: int
    concurrent_projects: int                  # multi-project count
    session_context: dict[str, Any]
    generated_at: float
```

**Key design decision:** ProductionPhase is DERIVED, not stored. The `phase` property reads subsystems and deterministically classifies based on what the organism is currently doing. Multi-project: if projects A and B are in different phases, the snapshot reports per-project phases + an overall organism phase.

**Completion invariant enforcement:** ProductionOpsRuntime is the arbiter of production completion. A production is not complete when packets are executed — it is complete when `ship_readiness()` returns READY (all quality dimensions pass, governance approves, proof package assembled). If proof fails, the production remains in REVIEWING phase and loops. If blocked, governance escalates. The `phase()` derivation enforces this: SHIPPING phase requires all checks green.

**Methods:** `phase()`, `snapshot()`, `active_productions()`, `what_ships_next()`, `blockers()`, `by_target(target_type)`, `is_complete(production_id)`, `summary()`

---

### C22.1 — Production Planning Runtime

**File:** `substrate/organism/production_planning_runtime.py` (~600 lines)
**Test:** `tests/test_c22_production_planning.py` (~50 tests)

**Purpose:** Convert any "Build X" intent into a complete professional software lifecycle — automatically including architecture, testing, security, observability, CI/CD, deployment, monitoring, recovery. The user says "Build X." The organism knows everything else that must happen.

**Composes (all lazy):**
- `WorkPacketEngine` (substrate/organism/work_packet_engine.py) — `decompose_intent_to_batch()`
- `GovernanceRuntime` — risk classification
- `TradeoffIntelligenceEngine` — displacement analysis
- `TrajectoryIntelligenceRuntime` — forecasting for prioritization

**New types (inline):**
```python
class ProductionDiscipline(str, Enum):
    """Every professional software lifecycle discipline.
    "Build X" automatically includes ALL of these."""
    ARCHITECTURE = "architecture"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    SECURITY = "security"
    OBSERVABILITY = "observability"
    DEPLOYMENT = "deployment"
    REVIEW = "review"
    DOCUMENTATION = "documentation"
    RECOVERY = "recovery"

@dataclass
class ProductionPlan:
    goal: str
    target: str                              # ProductionTarget value
    packets: list[dict[str, Any]]            # WorkPacket dicts
    dependency_order: list[str]              # packet IDs in execution order
    disciplines_covered: list[str]           # which disciplines this plan covers
    disciplines_deferred: list[str]          # which were intentionally skipped + why
    tradeoff_analysis: dict[str, Any]
    risk_summary: dict[str, Any]
    estimated_roles: list[dict[str, Any]]    # which org roles needed
    generated_at: float
```

**What's genuinely new (~40%):** Production lifecycle templates that automatically expand "Build X" into the full professional lifecycle:

```python
_PRODUCTION_TEMPLATES = {
    "full_product": [
        ("architecture", "Architecture & Design"),
        ("implementation", "Core Implementation"),
        ("testing", "Test Suite"),
        ("security", "Security Review"),
        ("observability", "Observability Setup"),
        ("deployment", "Deployment Pipeline"),
        ("review", "Code Review"),
        ("documentation", "Documentation"),
    ],
    "feature": [
        ("architecture", "Feature Design"),
        ("implementation", "Implementation"),
        ("testing", "Tests"),
        ("review", "Review"),
    ],
    "fix": [
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
    "infrastructure": [
        ("architecture", "Infrastructure Design"),
        ("implementation", "Implementation"),
        ("security", "Security Hardening"),
        ("observability", "Monitoring Setup"),
        ("deployment", "Deployment"),
        ("recovery", "Recovery Plan"),
    ],
}
```

The factory wraps `WorkPacketEngine.decompose_intent_to_batch()` — does NOT recreate packet logic. It adds: production-type classification (deterministic keyword matching), template selection, automatic discipline expansion, tradeoff analysis, role estimation.

**Methods:** `plan_production(goal, target, constraints)`, `classify_production_type(goal)`, `required_disciplines(production_type)`, `tradeoff_preview(goal)`, `summary()`

---

### C22.2 — Production Workforce Runtime

**File:** `substrate/organism/production_workforce_runtime.py` (~500 lines)
**Test:** `tests/test_c22_production_workforce.py` (~40 tests)

**Purpose:** Connect workforce to production work. Who should do this? With what authority? Who reviews? Who approves shipping?

**Composes (all lazy):**
- `AgentWorkforceRuntime` (substrate/workstation/agent_workforce_runtime.py) — idle/overloaded agents
- `ExecutionCoordinator` (substrate/organism/execution_coordinator.py) — execution plans, queue
- `AgentFleetRuntime` (substrate/organism/agent_fleet_runtime.py) — `assign()`, `dispatch()`
- `DelegationReadinessRuntime` (substrate/organism/delegation_readiness_runtime.py) — feasibility

**New types (inline):**
```python
class ProductionRole(str, Enum):
    """Organizational hierarchy for software production.
    Mirrors real org structure: Director → Lead → IC."""
    DIRECTOR = "director"          # owns the product/project
    ARCHITECT = "architect"        # owns technical decisions
    LEAD = "lead"                  # owns a discipline (frontend, backend, security)
    REVIEWER = "reviewer"          # reviews work product
    CONTRIBUTOR = "contributor"    # executes work packets
    OPERATOR = "operator"          # the human (highest authority)

class ProductionAuthority(str, Enum):
    """What each role can do without escalation."""
    PLAN = "plan"
    IMPLEMENT = "implement"
    REVIEW = "review"
    APPROVE = "approve"
    SHIP = "ship"
    OVERRIDE = "override"          # operator only

# Role → authority mapping (static, deterministic)
_ROLE_AUTHORITY: dict[str, list[str]] = {
    "operator": ["plan", "implement", "review", "approve", "ship", "override"],
    "director": ["plan", "review", "approve"],
    "architect": ["plan", "review"],
    "lead": ["plan", "implement", "review"],
    "reviewer": ["review"],
    "contributor": ["implement"],
}

@dataclass
class ProductionAssignment:
    packet_id: str
    role: str                              # ProductionRole
    agent_type: str
    assignment_rationale: dict[str, Any]   # from FleetAssignment
    authority: list[str]                   # ProductionAuthority values
    compute_node: str
    assigned_at: float

@dataclass
class ProductionProgress:
    total_packets: int
    by_role: dict[str, int]               # role → count
    by_status: dict[str, int]             # status → count
    agents_involved: list[dict[str, Any]] # agent + role + utilization
    concurrent_projects: int
```

**What's new (~25%):** Role-based assignment wrapping `AgentFleetRuntime.assign()`. The fleet scores by capability — this adds organizational authority constraints. A contributor can implement but not approve. A reviewer can review but not ship. The operator has override on everything.

**Methods:** `assign_production_work(packets, project_id)`, `production_progress(project_id)`, `role_for_discipline(discipline)`, `who_can_approve(packet_id)`, `who_is_overloaded()`, `who_is_idle()`, `org_chart(project_id)`, `summary()`

---

### C22.3 — Production Review Runtime

**File:** `substrate/organism/production_review_runtime.py` (~520 lines)
**Test:** `tests/test_c22_production_review.py` (~45 tests)

**Purpose:** Governed review layer. Not just code gates — covers the full professional review scope: tests, architecture, types, dependencies, projections, security, observability, deployment readiness.

**Composes (all lazy):**
- `UnifiedApprovalRuntime` (substrate/workstation/unified_approval_runtime.py) — pending approvals
- `GovernanceRuntime` (substrate/organism/governance_runtime.py) — authority evaluation
- `ReviewPackageBuilder` (substrate/meta_ide/review_package_builder.py) — proof assembly
- `TrajectoryIntelligenceRuntime` — risk prediction
- `LearningExtractionRuntime` — lessons from past reviews

**New types (inline):**
```python
class ReviewVerdict(str, Enum):
    READY = "ready"                        # all checks pass, ready to ship
    CHANGES_REQUIRED = "changes_required"  # specific issues found
    BLOCKED = "blocked"                    # hard blockers (missing deps, broken build)
    APPROVAL_PENDING = "approval_pending"  # checks pass, needs authority sign-off

class QualityDimension(str, Enum):
    """Professional review dimensions. All checked by default."""
    TESTS = "tests"
    ARCHITECTURE = "architecture"
    TYPE_COHERENCE = "type_coherence"
    DEPENDENCY_DIRECTION = "dependency_direction"
    PROJECTION_BOUNDARY = "projection_boundary"
    INSTANCE_CONTEXT = "instance_context"
    SECURITY = "security"
    OBSERVABILITY = "observability"
    DEPLOYMENT_READINESS = "deployment_readiness"

@dataclass
class QualityCheck:
    dimension: str                         # QualityDimension
    passed: bool
    details: str
    gate_script: str                       # e.g., "scripts/check_dependency_direction.py"
    severity: str                          # "blocking" | "warning" | "info"

@dataclass
class ProductionReviewResult:
    packet_id: str
    verdict: str                           # ReviewVerdict
    quality_checks: list[dict[str, Any]]
    proof_package: dict[str, Any] | None
    governance_evaluation: dict[str, Any]
    risk_assessment: dict[str, Any]
    blocking_reasons: list[str]
    reviewer_role: str                     # who reviewed
    generated_at: float
```

**What's genuinely new (~30%):** Expanded quality check runner. The 5 existing pre-commit gate scripts form the code quality base. On top: security dimension (deterministic checks for hardcoded secrets, open ports, unsafe patterns), observability dimension (logging/monitoring presence), deployment readiness (Dockerfile/compose/deploy script presence). All deterministic — no LLM. Uses `gated_subprocess_run()` from `substrate/execution/cpu_gate.py`.

**Methods:** `review_production(packet_id)`, `quality_status(packet_id)`, `pending_reviews()`, `review_history(limit)`, `ship_readiness(project_id)`, `summary()`

---

### C22.4 — Capability Compounding Runtime

**File:** `substrate/organism/capability_compounding_runtime.py` (~400 lines)
**Test:** `tests/test_c22_capability_compounding.py` (~35 tests)

**Purpose:** Operationalized learning. Outcome → Lesson → Pattern → Capability → Reusable Asset. Already target-agnostic — no changes from original plan beyond naming consistency.

**Composes (all lazy):**
- `LearningExtractionRuntime` (substrate/organism/learning_extraction_runtime.py)
- `InstitutionalMemoryRuntime` (substrate/organism/institutional_memory_runtime.py)
- `CapabilityEvolutionEngine` (substrate/organism/capability_evolution_engine.py)
- `OutcomePatternEngine` (substrate/organism/outcome_pattern_engine.py)
- `CompoundingEngine` (substrate/organism/compounding_engine.py)

**New types (inline):**
```python
class CompoundingStage(str, Enum):
    OUTCOME = "outcome"
    LESSON = "lesson"
    PATTERN = "pattern"
    CAPABILITY = "capability"
    OPERATIONAL = "operational"

@dataclass
class CompoundingSnapshot:
    total_outcomes: int
    total_lessons: int
    total_patterns: int
    capabilities_evolved: int
    pending_promotions: int
    institutional_health: str
    compounding_velocity: float
    reusable_assets: list[dict[str, Any]]
    generated_at: float
```

**Methods:** `snapshot()`, `production_to_asset_pipeline(production_id)`, `pending_promotions()`, `institutional_health()`, `reusable_assets()`, `summary()`

---

### C22.5 — Product Factory Runtime

**File:** `substrate/organism/product_factory_runtime.py` (~550 lines)
**Test:** `tests/test_c22_product_factory.py` (~45 tests)

**Purpose:** Given ANY software target definition, generate: goal tree, production plan, capability requirements. Handles all target types through the same pipeline — self-build and projection-build are the same capability. The target hierarchy is explicit and equal:
- **SUBSTRATE** — UMH itself (self-build)
- **PROJECTION** — EOS / LOS / COS (first-class, not secondary)
- **CLIENT_PRODUCT** — client SaaS products
- **INTERNAL_TOOL** — internal tooling
- **WEBSITE** — marketing sites, landing pages
- **AUTOMATION** — scripts, pipelines, integrations

**Composes (all lazy):**
- `ProjectionIntegrationRuntime` (substrate/organism/projection_integration_runtime.py) — projection-specific gap analysis
- `ProductionPlanningRuntime` (C22.1) — packet generation
- `GovernanceRuntime` — policy evaluation
- `TradeoffIntelligenceEngine` — displacement analysis

**New types (inline):**
```python
class ProductGoalType(str, Enum):
    INFRASTRUCTURE = "infrastructure"
    FEATURE = "feature"
    INTEGRATION = "integration"
    MIGRATION = "migration"
    CAPABILITY = "capability"
    LAUNCH = "launch"

@dataclass
class ProductGoal:
    goal_id: str
    product_id: str
    target_type: str                       # ProductionTarget value
    goal_type: str                         # ProductGoalType
    title: str
    description: str
    dependencies: list[str]
    priority: int
    risk_class: str

@dataclass
class ProductPlan:
    product_id: str
    product_name: str
    target_type: str                       # ProductionTarget value
    goals: list[dict[str, Any]]
    production_packets: list[dict[str, Any]]
    capability_requirements: list[str]
    gap_analysis: dict[str, Any]
    estimated_complexity: str
    estimated_roles: list[str]
    generated_at: float
```

**What's genuinely new (~40%):** Goal tree generation from product definition + gap analysis. Schema: `{id, name, target_type, goals: [{title, description, type}]}`. The factory treats all targets identically. For projection targets, it delegates gap analysis to `ProjectionIntegrationRuntime`. For other targets, it uses the goal tree directly.

**Methods:** `generate_product_plan(product_id, product_definition)`, `list_products()`, `product_readiness(product_id)`, `by_target_type(target_type)`, `summary()`

---

### C22.6 — Source Truth Runtime (CORE DELIVERABLE)

**File:** `substrate/organism/source_truth_runtime.py` (~500 lines)
**Test:** `tests/test_c22_source_truth.py` (~40 tests)

**Purpose:** Full organizational lineage — the runtime that makes UMH categorically better than Cursor/Replit/GitHub. Tracks the complete chain: Intent → Decision → Requirement → WorkPacket → Code → Review → Approval → Deployment → Outcome → Learning → Capability. GitHub tracks one layer (code). UMH tracks the full chain. This is not an auxiliary runtime — it is the core differentiator of governed software production.

**Composes (all lazy):**
- `DecisionRegistry` (substrate/organism/decision_registry.py) — decisions
- `WorkPacketEngine` (substrate/organism/work_packet_engine.py) — work packets
- `ExecutionCoordinator` (substrate/organism/execution_coordinator.py) — execution plans
- `LearningExtractionRuntime` (substrate/organism/learning_extraction_runtime.py) — lessons
- `CapabilityEvolutionEngine` (substrate/organism/capability_evolution_engine.py) — capabilities
- `GovernanceRuntime` — governance decisions

**New types (inline):**
```python
class LineageNodeType(str, Enum):
    INTENT = "intent"
    DECISION = "decision"
    REQUIREMENT = "requirement"
    WORK_PACKET = "work_packet"
    EXECUTION = "execution"
    REVIEW = "review"
    APPROVAL = "approval"
    DEPLOYMENT = "deployment"
    OUTCOME = "outcome"
    LESSON = "lesson"
    CAPABILITY = "capability"

@dataclass
class LineageNode:
    node_id: str
    node_type: str                         # LineageNodeType
    title: str
    source_id: str                         # ID in the source subsystem
    parent_id: str                         # upstream lineage node
    children: list[str]                    # downstream lineage nodes
    created_at: float
    metadata: dict[str, Any]

@dataclass
class LineageChain:
    chain_id: str
    root_intent: str
    nodes: list[dict[str, Any]]            # LineageNode dicts
    depth: int                             # how far the chain extends
    terminal_state: str                    # "completed" | "in_progress" | "failed"
    generated_at: float
```

**What's genuinely new (~50%):** Lineage graph construction. Given any node (a work packet, a decision, a capability), trace upstream to the original intent and downstream to the outcome/capability. The graph is assembled on-demand from existing subsystem data — NOT a separate store. Each subsystem already has its own persistence; this runtime reads across them to build the chain.

**Methods:** `trace_lineage(node_id, node_type)`, `intent_to_capability(intent_id)`, `why_does_this_exist(artifact_id)`, `full_chain(root_intent_id)`, `orphaned_work()`, `summary()`

---

### C22.7 — Production Surface Routes

**File:** `transports/api/cockpit_production_routes.py` (~250 lines)
**Test:** `tests/test_c22_production_routes.py` (~25 tests)
**Mount in:** `transports/api/cockpit.py` (add `_mount_production_router()` block — ~7 lines)

**Pattern:** Same as `cockpit_runtime_surface_routes.py` — FastAPI APIRouter, lazy singleton init, `configure()`.

**Endpoints (11):**
```
GET /production/snapshot          → ProductionOpsRuntime.snapshot()
GET /production/phase             → ProductionOpsRuntime.phase()
GET /production/active            → ProductionOpsRuntime.active_productions()
GET /production/workforce         → ProductionWorkforceRuntime.summary()
GET /production/workforce/chart   → ProductionWorkforceRuntime.org_chart()
GET /production/reviews           → ProductionReviewRuntime.pending_reviews()
GET /production/ship-readiness    → ProductionReviewRuntime.ship_readiness()
GET /production/learning          → CapabilityCompoundingRuntime.snapshot()
GET /production/compounding       → CapabilityCompoundingRuntime.pending_promotions()
GET /production/products          → ProductFactoryRuntime.list_products()
GET /production/lineage/{id}      → SourceTruthRuntime.trace_lineage()
```

---

### Type Registration

Add 9 new enums to `substrate/canonical_types.py`:
- `ProductionPhase` → `substrate.organism.production_ops_runtime`
- `ProductionTarget` → `substrate.organism.production_ops_runtime`
- `ProductionDiscipline` → `substrate.organism.production_planning_runtime`
- `ProductionRole` → `substrate.organism.production_workforce_runtime`
- `ProductionAuthority` → `substrate.organism.production_workforce_runtime`
- `ReviewVerdict` → `substrate.organism.production_review_runtime`
- `QualityDimension` → `substrate.organism.production_review_runtime`
- `CompoundingStage` → `substrate.organism.capability_compounding_runtime`
- `ProductGoalType` → `substrate.organism.product_factory_runtime`
- `LineageNodeType` → `substrate.organism.source_truth_runtime`

---

### Acceptance Tests

**File:** `tests/test_c22_acceptance.py` (~20 tests)

**AT1 — Full Production Loop:**
ProductionPlanningRuntime decomposes "Build user dashboard" → packets with ALL disciplines (architecture, testing, security, observability, deployment, review) → ProductionWorkforceRuntime assigns with roles (architect, contributor, reviewer) → ProductionReviewRuntime runs quality checks → CapabilityCompoundingRuntime snapshot shows pipeline.

**AT2 — Target-Agnostic (Same Pipeline):**
Run "Build EOS Dashboard" and "Build UMH feature" through ProductFactoryRuntime. Verify identical pipeline structure — only the target parameter differs.

**AT3 — Capability Reuse (Compounding Proven):**
Run AT1 twice. Second run should reference prior capability. CompoundingEngine tracks lineage.

**AT4 — Organizational Lineage:**
SourceTruthRuntime.trace_lineage() from a work packet traces upstream to original intent and downstream to outcome. Full chain verified.

**AT5 — Multi-Project Concurrent:**
Submit two production plans simultaneously. ProductionOpsRuntime.snapshot() shows concurrent_projects=2 with independent phases.

**AT6 — Voice-to-Production Queue:**
Simulate voice intent → ProductionOpsRuntime shows PLANNING phase → packets appear in production queue with full discipline coverage.

**AT7 — Completion Is Outcome-Based (Loop Until Done):**
Submit production with a failing quality check (e.g., missing tests). Verify ProductionOpsRuntime.is_complete() returns False and phase stays REVIEWING. Fix the quality check. Verify phase transitions to SHIPPING only after all proofs pass. Verify is_complete() only returns True after governance approval + proof package assembly.

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

1. `substrate/canonical_types.py` — add 10 type registrations
2. `transports/api/cockpit.py` — add `_mount_production_router()` block (~7 lines)

### Files Created (17)

| File | Est. Lines |
|------|-----------|
| `substrate/organism/production_ops_runtime.py` | ~450 |
| `substrate/organism/production_planning_runtime.py` | ~600 |
| `substrate/organism/production_workforce_runtime.py` | ~500 |
| `substrate/organism/production_review_runtime.py` | ~520 |
| `substrate/organism/capability_compounding_runtime.py` | ~400 |
| `substrate/organism/product_factory_runtime.py` | ~550 |
| `substrate/organism/source_truth_runtime.py` | ~500 |
| `transports/api/cockpit_production_routes.py` | ~250 |
| `tests/test_c22_production_ops_runtime.py` | ~400 |
| `tests/test_c22_production_planning.py` | ~500 |
| `tests/test_c22_production_workforce.py` | ~400 |
| `tests/test_c22_production_review.py` | ~450 |
| `tests/test_c22_capability_compounding.py` | ~350 |
| `tests/test_c22_product_factory.py` | ~450 |
| `tests/test_c22_source_truth.py` | ~400 |
| `tests/test_c22_production_routes.py` | ~250 |
| `tests/test_c22_acceptance.py` | ~300 |

**Total: ~6,720 LOC (runtimes + routes + tests)**
**~310 tests**

---

### Verification

After all files created:
1. `python3 -m py_compile` every new .py file
2. `python3 -m pytest tests/test_c22_*.py -v` — all ~310 tests pass
3. `python3 scripts/check_type_divergence.py --all` — no new violations
4. `python3 scripts/check_dependency_direction.py --all` — no violations
5. `python3 scripts/check_projection_leak.py --all` — no projection names in substrate/
6. `python3 scripts/check_instance_leak.py --all` — no instance context leaks
7. Import check for all 7 runtimes + route module
8. Cockpit mount: restart cockpit, verify `/api/umh/production/snapshot` returns JSON
