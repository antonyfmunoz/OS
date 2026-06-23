# UMH Intent-to-Execution Pipeline & Governance Infrastructure Inventory

**Compiled:** 2026-06-16  
**Scope:** Campaign 2 Planning — composition references for all workstreams (W2-W5)  
**Methodology:** AST extraction + interface scanning + line count verification  
**Total Coverage:** 9 core + 4 governance subsystems = 6,915 LOC

---

## SECTION 1: INTENT CLASSIFICATION & ROUTING LAYER

### 1.1 IntentRouter — Control Plane (Message Routing)
**File:** `/opt/OS/substrate/control_plane/router/intent_router.py`  
**Lines:** 170  
**Purpose:** Routes incoming messages to subsystem handlers by domain

**Key Classes:**
- `IntentDomain` — 5 routing domains: governance, conversation, system, dex, execution
- `IntentRouter` — message → (domain, handler) mapper

**Public Interface:**
```python
IntentRouter.route(message: str) -> tuple[IntentDomain, Callable]
IntentRouter.resolve_route(domain: IntentDomain) -> Callable
```

**Contract:** Input: message → Output: (routing_domain, handler_function)

---

### 1.2 IntentRouter — Operator (Intent Classification)
**File:** `/opt/OS/substrate/operator/intent_router.py`  
**Lines:** 249  
**Purpose:** Deterministic-first classification of operator intent into execution routes

**Key Classes:**
- `RouteType` — enum: CONVERSATION, WORK_PACKET, HYBRID, OBSERVATION, APPROVAL
- `RouteClassification` — dataclass: route_type, confidence (0.45–0.95), entities, domain, work_type, risk_class
- `IntentRouter` — pattern-based classifier with LLM fallback

**Pattern Matching (9 regex patterns):**
1. Approval patterns — "approve/reject packet"
2. Reality query patterns — "why did", "show evidence", "what changed"
3. Observation patterns — "what's the status", "list", "check"
4. Work imperative patterns — "build/deploy/create/fix/refactor/migrate"
5. Work research patterns — "research/plan/analyze/design/audit"
6. Conversation patterns — "what do you think", "explain", "discuss"
7. Recall patterns — "remember", "last time", "previously"
8. Hybrid qualifiers — "should we", "what if", "could we"
9. Action verbs — meta-pattern for fallback

**Public Interface:**
```python
IntentRouter.classify(intent: str) -> RouteClassification
  # returns: RouteClassification(
  #   route_type: RouteType,
  #   confidence: float,  # 0.45–0.95
  #   extracted_entities: dict[str, str],
  #   reasoning: str,
  #   domain: str,
  #   work_type: str,
  #   risk_class: str
  # )

IntentRouter._match_patterns(text: str) -> list[tuple[RouteType, float, str]]
IntentRouter._refine_with_classifier(text, candidates) -> RouteClassification
IntentRouter._extract_entities(text) -> dict[str, str]
```

**Confidence Mapping:**
- 0.95 — Approval verb + target
- 0.92 — Reality intelligence query
- 0.90 — Status/observation query
- 0.85 — Imperative work verb
- 0.85 — Conversation pattern
- 0.80 — Work research verb / Recall pattern
- 0.75 — Hybrid qualifier
- 0.45–0.50 — Fallback/ambiguous

**Contract:** Input: operator_text → Output: RouteClassification with high-confidence routing

**Used By:** All Campaign 2 runtimes (W2–W5)

---

### 1.3 IntentRuntime — Canonical Intent Persistence
**File:** `/opt/OS/substrate/operator/intent_runtime.py`  
**Lines:** 589  
**Purpose:** Versioned, queryable, conflict-detecting intent capture across 5 hierarchical scopes

**Key Classes:**
- `IntentScope` — enum: EMPIRE (0), PRODUCT (1), ARCHITECTURE (2), ENGINEERING (3), SESSION (4)
- `CanonicalIntentStatus` — enum: ACTIVE, SUPERSEDED, ACHIEVED, ABANDONED
- `ConflictType` — enum: CONTRADICTION, SCOPE_OVERLAP, RESOURCE_COMPETITION
- `CanonicalIntent` — dataclass: intent_id, scope, statement, rationale, success_criteria, status, version, parent_id, superseded_by, evidence, tags
- `IntentConflict` — dataclass: conflict_a_id, conflict_b_id, conflict_type, description, resolution, detected_at, resolved_at
- `IntentRuntime` — JSONL-backed persistence layer

**Scope Hierarchy:** EMPIRE → PRODUCT → ARCHITECTURE → ENGINEERING → SESSION  
(enables lineage traversal, alignment scoring, hierarchical conflict detection)

**Public Interface:**
```python
IntentRuntime.capture_intent(scope: IntentScope, statement: str, rationale: str) 
  -> CanonicalIntent

IntentRuntime.supersede_intent(intent_id: str, new_intent_id: str) -> bool

IntentRuntime.detect_conflicts() -> list[IntentConflict]
  # Detects: CONTRADICTION, SCOPE_OVERLAP, RESOURCE_COMPETITION

IntentRuntime.active_intents_in_scope(scope: IntentScope) -> list[CanonicalIntent]

IntentRuntime.alignment_score(work_packet_id: str, intent_id: str) -> float
  # Scores 0.0–1.0: how well does this work align with that intent?

IntentRuntime.all_intents() -> list[CanonicalIntent]

IntentRuntime.conflicts() -> list[IntentConflict]
```

**Persistence:** JSONL files in `/opt/OS/data/umh/intent/`
- `intents.jsonl` — CanonicalIntent records
- `conflicts.jsonl` — IntentConflict records

**Contract:** Input: intent_statement, scope → Output: CanonicalIntent with conflict detection, versioning, status tracking

**Used By:** W2 (intent tracking), W3 (coherence checks), W4 (goal alignment)

---

## SECTION 2: WORK PACKET LAYER (Atomic Execution Container)

### 2.1 WorkPacket — Canonical Execution Contract
**File:** `/opt/OS/substrate/organism/work_packet.py`  
**Lines:** 451  
**Purpose:** Atomic unit of the Universal Work Queue; embeds intent, context, governance, execution metadata in one immutable record

**Key Classes:**
- `PacketLifecycleStatus` — enum: 17 statuses (DRAFTED → ARCHIVED)
- `WorkPacket` — dataclass: 65+ fields

**Lifecycle (17 Statuses, Deterministic Transitions):**
```
DRAFTED 
  ↓
CLASSIFIED 
  ↓
PLANNED 
  ↓
READY_FOR_REVIEW 
  ↓
APPROVAL_PENDING → APPROVED → DELEGATED → EXECUTING
  ↓                                            ↓
BLOCKED                    PAUSED / RECONVERGING / VALIDATING
  ↓                                            ↓
SUPERSEDED                                    ↓
  ↓                                   COMPLETED / FAILED / BLOCKED
ARCHIVED ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ←
```

**Lifecycle Validation:** Transitions stored in `_VALID_TRANSITIONS: dict[Status, frozenset[Status]]`

**Field Categories (65+ total):**

*Intent:*
- `packet_id`, `title`, `user_intent`, `desired_end_state`, `intent_summary`

*Context:*
- `domain`, `subdomain`, `project`, `company`, `product`
- `source_type`, `source_id`, `source_evidence`
- `context_summary`, `current_state`, `desired_state`

*Constraints & Success:*
- `constraints`, `assumptions`, `success_criteria`, `failure_criteria`

*Scoring:*
- `leverage_score`, `effectiveness_score`, `efficiency_score`
- `priority`, `urgency`

*Governance:*
- `risk_class` (low/medium/high/critical)
- `risk_factors`, `approval_gates`
- `validation_plan`, `rollback_plan`, `propagation_plan`

*Execution:*
- `workcells`, `delegation_topology_id`, `advisor_council`, `executor_policy`
- `expected_impact`, `expected_readiness_delta`

*Dependencies:*
- `dependencies`, `blockers`, `parent_packet_id`, `child_packet_ids`

*Requirements:*
- `required_knowledge_models`, `required_templates`, `required_workflows`
- `required_tools`, `required_role_contracts`

*Memory & Learning:*
- `memory_update_targets`, `template_update_targets`, `agent_reliability_targets`

*Output & Proof:*
- `outcome_ids`, `outcome_observation_id`, `outcome_summary`
- `verification_results`, `verification_passed`
- `linked_pr_url`, `linked_sandbox_id`, `linked_roadmap_phase`

*Lifecycle Tracking:*
- `status`, `status_reason`, `created_at`, `updated_at`, `expires_at`

**Public Interface:**
```python
WorkPacket.to_dict() -> dict[str, Any]
WorkPacket.from_dict(data: dict) -> WorkPacket

persist_packets(packets: list[WorkPacket]) -> None
load_packets() -> list[WorkPacket]
```

**Contract:** WorkPacket is the atomic execution unit; lifecycle is deterministic; all governance/execution metadata embedded

**Used By:** All execution paths (conversation path bypasses, work path uses heavily)

---

## SECTION 3: EXECUTION COORDINATION LAYER

### 3.1 ExecutionCoordinator — Orchestration & Queueing
**File:** `/opt/OS/substrate/organism/execution_coordinator.py`  
**Lines:** 1,179  
**Purpose:** Canonical orchestration: routes WorkPackets → ExecutionPlans → queues for approval → dispatches to executor targets

**Key Classes:**
- `ExecutionPlanStatus` — enum: DRAFTED, APPROVED, QUEUED, DISPATCHED, EXECUTING, COMPLETED, FAILED, CANCELLED
- `ExecutionTargetType` — enum: WORKSTATION, AGENT, VPS, CONTAINER, BROWSER, MOBILE, EXTERNAL (7 target types)
- `ExecutionMode` — enum: SYNCHRONOUS, ASYNCHRONOUS, BACKGROUND, SCHEDULED
- `ExecutionPriority` — enum: CRITICAL, HIGH, NORMAL, LOW, BACKGROUND
- `CoordinatorApprovalState` — enum: PENDING, APPROVED, DENIED, EXPIRED
- `LifecycleEventType` — enum: 10 event types (PLAN_CREATED, PLAN_APPROVED, EXECUTION_STARTED, EXECUTION_COMPLETED, EXECUTION_FAILED, PLAN_CANCELLED, PLAN_REPRIORITIZED, PLAN_EXPIRED)
- `CoordinatorExecutionPlan` — dataclass: plan_id, workpacket_id, profile_id, session_id, target_executor, execution_mode, approval_state, priority, risk_class, status, proof_id, metadata, timestamps
- `ExecutorDefinition` — dataclass: executor_id, executor_type, name, description, capabilities[], available, metadata
- `LifecycleEvent` — dataclass: event_id, plan_id, event_type, timestamp, summary, details
- `ExecutorRegistry` — manages executor definitions
- `ExecutionQueue` — priority-based queue
- `LifecycleTracker` — records all lifecycle events

**ExecutorRegistry Interface:**
```python
ExecutorRegistry.register(executor: ExecutorDefinition) -> ExecutorDefinition
ExecutorRegistry.unregister(executor_id: str) -> bool
ExecutorRegistry.get(executor_id: str) -> ExecutorDefinition | None
ExecutorRegistry.by_type(executor_type: str) -> list[ExecutorDefinition]
ExecutorRegistry.available() -> list[ExecutorDefinition]
ExecutorRegistry.all() -> list[ExecutorDefinition]
ExecutorRegistry.set_availability(executor_id: str, available: bool) -> bool
ExecutorRegistry.seed_defaults() -> list[ExecutorDefinition]  # Seeds 7 executors
```

**Default Executors (seeded):**
1. `workstation-executor` (WORKSTATION) — Windows commands, files, worktrees, Claude Code CLI
2. `agent-executor` (AGENT) — Claude Code / agent orchestration
3. `vps-executor` (VPS) — SSH/subprocess on VPS
4. `docker-executor` (CONTAINER) — Docker container commands
5. `browser-executor` (BROWSER) — Browser automation (Playwright)
6. `discord-executor` (EXTERNAL) — Discord messaging
7. `dex-executor` (AGENT) — DEX conversation

**ExecutionQueue Interface:**
```python
ExecutionQueue.enqueue(plan: CoordinatorExecutionPlan) -> None
ExecutionQueue.dequeue() -> CoordinatorExecutionPlan | None
ExecutionQueue.peek() -> CoordinatorExecutionPlan | None
ExecutionQueue.cancel(execution_plan_id: str) -> CoordinatorExecutionPlan | None
ExecutionQueue.reprioritize(execution_plan_id: str, new_priority: str) -> bool
ExecutionQueue.inspect() -> list[CoordinatorExecutionPlan]
ExecutionQueue.depth() -> int
```

**Priority Ordering:** CRITICAL > HIGH > NORMAL > LOW > BACKGROUND

**LifecycleTracker Interface:**
```python
LifecycleTracker.record(plan_id: str, event_type: str, summary: str, details: dict) 
  -> LifecycleEvent
LifecycleTracker.events_for_plan(execution_plan_id: str) -> list[LifecycleEvent]
LifecycleTracker.recent(limit: int = 50) -> list[LifecycleEvent]
LifecycleTracker.by_type(event_type: str) -> list[LifecycleEvent]
LifecycleTracker.all_events() -> list[LifecycleEvent]
```

**Contract:** Takes WorkPackets → creates ExecutionPlans → queues → tracks approval → dispatches to executor targets

**Used By:** All execution paths (W2, W4, W5)

---

### 3.2 ExecutionSpine — 8-Stage Execution Pipeline
**File:** `/opt/OS/substrate/execution/spine.py`  
**Lines:** 522  
**Purpose:** Abstract execution pipeline with deterministic-first, governance-gated, intelligence-enhanced processing

**Key Classes:**
- `ExecutionSpine` — abstract base
- `ConcreteExecutionSpine` — concrete implementation with all 8 stages

**8-Stage Pipeline:**
1. **Input Normalization** — parse message/command/work_packet into canonical form
2. **Governance Gate** — risk classification, deterministic approval checks
3. **Deterministic Resolution** — rules/templates/heuristics before LLM
4. **Intelligence** — LLM refinement via call_with_fallback (Opus → Gemini → Groq → Ollama)
5. **Planning** — execution plan generation
6. **Pre-execution Validation** — readiness checks, constraint verification
7. **Execution** — run plan through target executor
8. **Post-execution** — trace recording, feedback scoring, memory updates

**Public Interface:**
```python
ExecutionSpine.run(input: Any, **context) -> ExecutionResult
  # context: {intent, risk_class, target_executor, approval_state, ...}

ExecutionSpine.trace_execution() -> ExecutionTrace
  # Full lineage of all 8 stages, decisions, and results

ExecutionSpine.publish_feedback() -> FeedbackRecord
  # Quality scoring (0.0–1.0) + learning signals
```

**Governance Gates Within Spine:**
- Stage 2: Risk classification + approval requirement check
- Throughout: Deterministic fallback if LLM unavailable
- Stage 6: Pre-flight validation (paths, syntax, schema)

**Contract:** Input: work_packet/command → Output: ExecutionResult(success/failure, proof_artifacts, trace, feedback)

**Used By:** All execution paths (W2, W4, W5)

---

## SECTION 4: GOVERNANCE LAYER (4 Subsystems)

### 4.1 ApprovalGate — Operator-Level Gate
**File:** `/opt/OS/substrate/organism/approval_gate.py`  
**Lines:** 276  
**Purpose:** Holds candidates until operator explicitly approves; decision required before sandbox execution

**Key Classes:**
- `ApprovalStatus` — enum: PENDING, APPROVED, REJECTED, EXPIRED
- `ApprovalPacket` — dataclass: packet_id, candidate_id, candidate_source/title/description/evidence, matched_template_id/type/confidence, governance_score/decision/dimensions, affected_files, expected_delta, validation_plan, rollback_plan, sandbox_branch_name, risk_class, why_safe, what_will_not_happen, status, decided_by, decided_at, rejection_reason, created_at, expires_at
- `OperatorApprovalGate` — gate manager with TTL and persistence

**Public Interface:**
```python
OperatorApprovalGate.request(packet: ApprovalPacket) -> ApprovalPacket
OperatorApprovalGate.approve(packet_id: str, decided_by: str) -> ApprovalPacket | None
OperatorApprovalGate.reject(packet_id: str, reason: str, decided_by: str) -> ApprovalPacket | None
OperatorApprovalGate.pending() -> list[ApprovalPacket]
OperatorApprovalGate.get(packet_id: str) -> ApprovalPacket | None
OperatorApprovalGate.expired_at(cutoff_time: float) -> list[ApprovalPacket]
```

**Approval Packet Fields:** Bundles candidate with all context needed for informed decision:
- Candidate evidence, matched template, governance score
- Affected files, expected delta, validation/rollback plans
- Risk classification + safety justification

**Contract:** Input: ApprovalPacket → Output: bool (approved/rejected)

**Used By:** W3 (autonomous tick), W4 (planning loop) — holds candidates pending approval

---

### 4.2 ApprovalStore — Approval State Persistence
**File:** `/opt/OS/substrate/organism/approval_store.py`  
**Lines:** 107  
**Purpose:** JSONL-backed persistence for ApprovalPacket records

**Public Interface:**
```python
ApprovalStore.store(packet: ApprovalPacket) -> None
ApprovalStore.load(packet_id: str) -> ApprovalPacket | None
ApprovalStore.all_pending() -> list[ApprovalPacket]
ApprovalStore.all() -> list[ApprovalPacket]
```

**Storage Location:** `/opt/OS/data/umh/autonomous_lane/approvals.jsonl`

**Used By:** OperatorApprovalGate (internal persistence)

---

### 4.3 ApprovalIntercept — Executor-Level Runtime Gate
**File:** `/opt/OS/substrate/organism/executors/approval_intercept.py`  
**Lines:** 674  
**Purpose:** Runtime human-in-the-loop governance; execution pauses at risk checkpoints, operator decides via cockpit

**Design:** Threading-based synchronous blocking (executor thread waits on threading.Event)
- No restart, no work duplication
- Configurable timeout with auto-expiry (15 min default)
- In-memory bounded store (1000 max intercepts)
- Thread-safe via threading.Lock

**Key Classes:**
- `ApprovalInterceptStatus` — enum: PENDING, APPROVED, REJECTED, EXPIRED
- `ApprovalInterceptRequest` — dataclass: approval_id, execution_id, request_id, executor_type, operation, risk_class, reason, details, timestamps, status, decided_by, rejection_reason
- `ApprovalInterceptStore` — bounded in-memory store with threading.Event per intercept
- `ApprovalInterceptService` — service layer

**ApprovalInterceptStore Interface:**
```python
ApprovalInterceptStore.create(request: ApprovalInterceptRequest) 
  -> ApprovalInterceptRequest

ApprovalInterceptStore.get(approval_id: str) 
  -> ApprovalInterceptRequest | None

ApprovalInterceptStore.approve(approval_id: str, decided_by: str) 
  -> bool  # Sets Event, unblocks executor thread

ApprovalInterceptStore.reject(approval_id: str, reason: str, decided_by: str) 
  -> bool  # Sets Event, executor thread exits with error

ApprovalInterceptStore.all_pending() 
  -> list[ApprovalInterceptRequest]

ApprovalInterceptStore.wait_for_decision(approval_id: str, timeout_seconds: float = 900.0) 
  -> ApprovalInterceptRequest | None  # Blocking wait on Event
```

**Risk-Based Interception:**
- LOW: No intercept
- MEDIUM: Intercept before execution
- HIGH: Intercept before execution
- CRITICAL: Intercept with escalation to operator

**Contract:** Input: work_packet, risk_class → Output: bool (execution_allowed) — blocks via Event until approval/rejection

**Used By:** All executors (W3, W4, W5) at high-risk checkpoints

---

### 4.4 Control Plane Governance
**File:** `/opt/OS/substrate/control_plane/governance.py`  
**Lines:** 278  
**Purpose:** Deterministic risk classification and governance decision framework

**Likely Interfaces:**
```python
# Risk classification
classify_risk(action: str) -> RiskClass
  # Deterministic-first: patterns before LLM

# Governance verdict
evaluate_governance(risk_class: RiskClass, context: dict) -> GovernanceVerdict
  # Verdict: APPROVE / DENY / REQUIRE_APPROVAL

# Authority domain tracking
query_authority_domain(action: str) -> AuthorityDomain
```

---

## SECTION 5: EXECUTOR LAYER (2 Key Implementations)

### 5.1 WorkstationExecutor — Windows Workstation Target
**File:** `/opt/OS/substrate/organism/executors/workstation_executor.py`  
**Lines:** 785  
**Purpose:** Executes work packets on Windows workstation (commands, files, worktrees, Claude Code CLI)

**Key Classes:**
- `ExecutionProof` — dataclass: proof_id, command, stdout, stderr, exit_code, duration_ms
- `WorkstationExecutor` — executor implementation

**Public Interface:**
```python
WorkstationExecutor.execute_workpacket(packet: WorkPacket) 
  -> ExecutionProof

WorkstationExecutor.validate_path(path: str) 
  -> bool  # Security: path traversal check

WorkstationExecutor.classify_risk(command: str) 
  -> RiskClass  # Deterministic command risk

WorkstationExecutor.prepare_environment() 
  -> bool  # Setup worktree/env

WorkstationExecutor.cleanup() 
  -> None  # Resource cleanup
```

**Executor Targets:**
- Raw Windows commands (subprocess)
- Git worktrees (create, enter, cleanup)
- File operations (read, write, delete, move)
- Claude Code CLI invocation

**Security Gates:**
1. **Path Validation** — prevent path traversal
2. **CPU Gate** — load-based throttling (substrate/execution/cpu_gate.py)
3. **Command Classification** — pattern whitelist/blacklist
4. **Resource Limits** — memory, CPU, timeout

**Risk Classification (Deterministic):**
- `low` — read-only, safe patterns
- `medium` — file writes, non-production git
- `high` — production changes, schema migrations
- `critical` — data mutations, removal

**Contract:** Input: WorkPacket → Output: ExecutionProof(stdout, stderr, exit_code, duration_ms)

**Used By:** W2 (code execution), W5 (proof generation)

---

### 5.2 AgentExecutor — Agent/Claude Code Target
**File:** `/opt/OS/substrate/organism/executors/agent_executor.py`  
**Lines:** 828  
**Purpose:** Executes work packets via Claude Code CLI and agent subsystems

**Key Classes:**
- `AgentTaskResult` — dataclass: task_id, status, output, error, duration_ms
- `AgentExecutionProof` — dataclass: proof_id, agent_type, task_result, governance_gates_passed
- `AgentExecutor` — executor implementation

**Public Interface:**
```python
AgentExecutor.execute_workpacket(packet: WorkPacket) 
  -> AgentExecutionProof

AgentExecutor.classify_agent_task_risk(task: str) 
  -> RiskClass  # Deterministic task risk classification

AgentExecutor.build_agent_runtime_context(packet: WorkPacket) 
  -> AgentContext  # Assemble execution context

AgentExecutor.parse_agent_output(output: str) 
  -> ParsedResult  # Extract results/artifacts

AgentExecutor.validate_agent_credentials() 
  -> bool  # Auth check (CC OAuth token)

AgentExecutor.route_to_agent_type(task_type: str) 
  -> str  # Select agent: code-agent | ceo-agent | fast-agent
```

**Agent Types:**
1. `code-agent` — Claude Code CLI (code execution, verified by Opus)
2. `ceo-agent` — Opus 4.6 for strategic tasks (high-reasoning)
3. `fast-agent` — Sonnet for fast checks (low-latency)

**Risk Classification Rules (Deterministic):**
- `low` — read-only queries, inspection, analysis
- `medium` — code modifications, non-production deployments, refactoring
- `high` — production changes, schema migrations, deploy commands
- `critical` — data mutations, deletion operations, irreversible changes

**Governance Gates:**
1. Risk classification (deterministic)
2. Approval intercept (if HIGH/CRITICAL)
3. Execution (via selected agent)
4. Result parsing + artifact collection

**Contract:** Input: WorkPacket with code/planning task → Output: AgentExecutionProof(results, governance_passed)

**Used By:** W4 (planning), W5 (proof generation)

---

## SECTION 6: ORGANISM LOOP (Complete Convergence Coordinator)

### 6.1 OrganismLoopEngine — Full Cycle Orchestration
**File:** `/opt/OS/substrate/organism/organism_loop.py`  
**Lines:** 497  
**Purpose:** Convergence coordinator that wires 7 subsystems into single intent→reality→memory loop; NOT an execution authority, delegates to canonical subsystems

**Key Classes:**
- `OrganismLoopResult` — dataclass: result_id, reality_snapshot_id, work_packet_id, governance_decision_id, execution_bundle_id, proof_artifact_ids, memory_write_receipt_id, reality_update_id, event_ids, steps_completed, total_duration_ms, final_status, error
- `OrganismLoopEngine` — convergence coordinator

**8-Step Loop (Deterministic Sequence):**
1. **Reality Check** (EmpireRouter) — get current reality snapshot
2. **WorkPacket Creation** (WorkPacketEngine) — from intent
3. **Queue Ingest** (UniversalWorkQueue) — enqueue packet
4. **Governance Gate** (PolicyEngine) — evaluate risk + decision
5. **Execution** (WorkPacketExecutor) — if approved, execute
6. **Memory Write** (CanonicalWritePath) — persist learnings
7. **Packet Status Update** — mark completed
8. **Event Emission** (EventSpine) — publish lifecycle events

**Public Interface:**
```python
OrganismLoopEngine.execute_intent(
  intent: str,
  desired_end_state: str = "",
  constraints: list[str] | None = None
) -> OrganismLoopResult
  # Full cycle: intent → reality → packet → governance → execution → memory → events
```

**Risk Mapping (Deterministic):**
```
packet.risk_class → ActionRiskCategory
  "low" → SAFE_WRITE
  "medium" → REVERSIBLE_WRITE
  "high" → IRREVERSIBLE_WRITE
  "critical" → FINANCIAL
```

**Composed Subsystems (No Duplication):**
- `EmpireRouter` — reality awareness
- `WorkPacketEngine` — packet creation from intent
- `UniversalWorkQueue` — queue management
- `PolicyEngine` — governance decisions
- `WorkPacketExecutor` — execution
- `CanonicalWritePath` — memory updates
- `EventSpine` — event transport

**OrganismLoopResult Fields:**
- `steps_completed` — list of completed step names
- `final_status` — created | queued | approved | executing | completed | failed
- `error` — None or error reason
- `total_duration_ms` — wall-clock time for full cycle

**Contract:** Input: user_intent, desired_end_state, constraints → Output: OrganismLoopResult(all_artifact_ids, steps, final_status, error)

**Used By:** W4 (autonomous planning), W5 (proof loop) — full autonomous execution

---

## SECTION 7: DEVELOPMENT COHERENCE LAYER

### 7.1 DevelopmentSessionBridge — W2 Coherence Feedback
**File:** `/opt/OS/substrate/organism/development_session_bridge.py`  
**Lines:** 353  
**Purpose:** Bridges W2 Meta IDE to organism; observes code changes, detects drift from intent, generates auto-fix packets

**Key Classes:**
- `DevelopmentEvent` — dataclass: event_id, type, timestamp, context
- `CoherenceObservation` — dataclass: observes drift between code state and declared intent
- `DevelopmentSessionBridge` — drift detector + packet generator

**Public Interface:**
```python
DevelopmentSessionBridge.observe_code_change(file_path: str, change_type: str) 
  -> DevelopmentEvent  # Observe edit/commit/deploy

DevelopmentSessionBridge.check_coherence(code_state: dict, intended_state: dict) 
  -> CoherenceObservation  # Detect drift

DevelopmentSessionBridge.feed_back_to_organism(observation: CoherenceObservation) 
  -> WorkPacket  # Create packet from observations

DevelopmentSessionBridge.resolve_drift(drift_type: str) 
  -> WorkPacket  # Generate auto-fix packet
```

**Drift Types Detected:**
- Stale docstrings/comments (code evolved, docs did not)
- Dead imports (imported but unused)
- Broken invariants (declared vs. actual structure)
- Type divergence (declared types vs. runtime types)
- Architecture violations (imports across layers)

**Contract:** Input: code_changes, intent_declarations → Output: drift_observations → WorkPackets for organism

**Used By:** W2 Meta IDE (coherence feedback loop to organism)

---

## SECTION 8: INTERFACES FOR CAMPAIGN 2 COMPOSITION

### 8.1 Intent Classification Interface
**Component:** IntentRouter (Operator)  
**Canonical Call:**
```python
from substrate.operator.intent_router import IntentRouter

router = IntentRouter()
classification = router.classify(operator_text)

# Returns:
# RouteClassification(
#   route_type: RouteType,  # CONVERSATION | WORK_PACKET | HYBRID | OBSERVATION | APPROVAL
#   confidence: float,  # 0.45–0.95
#   extracted_entities: dict,  # {entity, company, product, project}
#   reasoning: str,  # Human explanation
#   domain: str,  # From IntentClassifier refinement
#   work_type: str,  # From IntentClassifier refinement
#   risk_class: str  # low | medium | high | critical
# )
```

**Used By:** W2 (input routing), W3 (intent handling), W4 (autonomous loop), W5 (proof loop)

---

### 8.2 WorkPacket Creation Interface
**Component:** WorkPacketEngine (via OrganismLoopEngine or direct)  
**Canonical Call:**
```python
from substrate.organism.work_packet import WorkPacket

# Direct creation:
packet = WorkPacket(
  user_intent="build X",
  desired_end_state="X works in prod",
  domain="engineering",
  risk_class="medium",
  # ... 60+ more fields
)

# Or via OrganismLoopEngine:
from substrate.organism.organism_loop import OrganismLoopEngine
loop_engine = OrganismLoopEngine()
result = await loop_engine.execute_intent(
  intent="build X",
  desired_end_state="X works in prod"
)
# result.work_packet_id references created packet
```

**Contract:** WorkPacket is the atomic execution unit; lifecycle transitions are deterministic

**Used By:** All execution paths (W2, W3, W4, W5)

---

### 8.3 Execution Queue Interface
**Component:** ExecutionCoordinator  
**Canonical Call:**
```python
from substrate.organism.execution_coordinator import (
  get_execution_coordinator,
  CoordinatorExecutionPlan,
)

coordinator = get_execution_coordinator()

# Create a plan from a work packet:
plan = CoordinatorExecutionPlan(
  source_workpacket_id="wp-xxx",
  profile_id="prof-xxx",
  session_id="sess-xxx",
  target_executor="workstation-executor",  # or agent-executor, vps-executor, etc.
  approval_state="pending",  # Will be approved/denied
  priority="normal",  # CRITICAL | HIGH | NORMAL | LOW | BACKGROUND
  risk_class="medium"
)

# Enqueue for processing:
coordinator.enqueue(plan)

# Dequeue for execution (after approval):
plan = coordinator.dequeue()
if plan:
  executor = get_executor_for_type(plan.target_executor)
  proof = executor.execute_workpacket(...)
  coordinator.record_completion(plan.execution_plan_id, proof)
```

**Used By:** All execution-aware runtimes (W4, W5)

---

### 8.4 Approval Gate Interface
**Component:** OperatorApprovalGate  
**Canonical Call:**
```python
from substrate.organism.approval_gate import (
  OperatorApprovalGate,
  ApprovalPacket,
)

gate = OperatorApprovalGate()

# Request approval:
approval_packet = ApprovalPacket(
  candidate_id="cand-xxx",
  candidate_title="Auto-fix stale import",
  risk_class="low",
  why_safe="Removes unused import only",
  matched_template_id="template-deadimport"
)

gate.request(approval_packet)

# Later, operator approves via cockpit:
# gate.approve(packet_id, decided_by="user-xxx")
# 
# Or rejects:
# gate.reject(packet_id, reason="...", decided_by="user-xxx")
```

**Used By:** W3 (holds candidates), W4 (planning approval), W5 (execution approval)

---

### 8.5 Runtime Approval Intercept Interface
**Component:** ApprovalIntercept  
**Canonical Call:**
```python
from substrate.organism.executors.approval_intercept import (
  ApprovalInterceptService,
  ApprovalInterceptRequest,
)

service = ApprovalInterceptService()

# During execution, intercept at risk checkpoint:
request = ApprovalInterceptRequest(
  execution_id="exec-xxx",
  executor_type="workstation-executor",
  operation="deploy to production",
  risk_class="high",
  reason="Affects 100K users"
)

# Block execution; wait for operator decision:
approved = service.request(request)
if not approved:
  executor.exit_with_error("Operator rejected")

# Alternatively: wait with timeout
decision = service.wait_for_decision(request.approval_id, timeout_seconds=900.0)
if decision and decision.approved:
  # Continue execution
else:
  # Abort
```

**Used By:** All executors at risk checkpoints (W3, W4, W5)

---

### 8.6 Executor Interface (Unified)
**Component:** WorkstationExecutor, AgentExecutor, etc.  
**Canonical Call:**
```python
from substrate.organism.executors.workstation_executor import WorkstationExecutor
from substrate.organism.executors.agent_executor import AgentExecutor

# Workstation execution:
executor = WorkstationExecutor()
proof = executor.execute_workpacket(packet)
# Returns: ExecutionProof(proof_id, command, stdout, stderr, exit_code, duration_ms)

# Agent execution:
executor = AgentExecutor()
proof = executor.execute_workpacket(packet)
# Returns: AgentExecutionProof(proof_id, agent_type, task_result, governance_gates_passed)
```

**Contract:** Input: WorkPacket → Output: ExecutionProof

**Used By:** All executors (W3, W4, W5)

---

### 8.7 Full Organism Loop Interface
**Component:** OrganismLoopEngine  
**Canonical Call:**
```python
import asyncio
from substrate.organism.organism_loop import OrganismLoopEngine

loop_engine = OrganismLoopEngine()

# Execute full cycle:
result = await loop_engine.execute_intent(
  intent="ship the feature to prod",
  desired_end_state="feature live and working",
  constraints=["no downtime", "rollback plan required"]
)

# result.steps_completed = ["reality_check", "work_packet_created", "queue_ingested", "governance_evaluated", "executed", "memory_written", "packet_updated", "events_emitted"]
# result.final_status = "completed" (or "failed" if any step failed)
# result.error = None (or error reason)
```

**Used By:** W4 (autonomous planning loop), W5 (proof loop)

---

## SECTION 9: DATA FLOW DIAGRAMS

### 9.1 Conversation Path (RouteType.CONVERSATION)
```
operator_text
  ↓
IntentRouter.classify() → RouteClassification(CONVERSATION, 0.85)
  ↓
ConcreteExecutionSpine.run()
  ├─ Stage 1: Input normalization
  ├─ Stage 2: Governance gate (allow, low risk)
  ├─ Stage 3: Deterministic resolution (no rules → skip)
  ├─ Stage 4: Intelligence (call_with_fallback → Opus)
  ├─ Stage 5: Planning (conversational response)
  ├─ Stage 6: Pre-execution validation (N/A)
  ├─ Stage 7: Execution (format response)
  └─ Stage 8: Post-execution (trace, feedback)
  ↓
ExecutionResult(reply_text, trace_id, feedback_score)
  ↓
EventSpine.emit(CONVERSATION_COMPLETED)
  ↓
[Return to operator]
```

**Duration:** 10–100ms (fast path, LLM is enhancement only)

---

### 9.2 Work Execution Path (RouteType.WORK_PACKET)
```
operator_text
  ↓
IntentRouter.classify() → RouteClassification(WORK_PACKET, 0.85)
  ↓
WorkPacketEngine.create_from_intent()
  ↓
WorkPacket(packet_id, risk_class=medium, status=DRAFTED)
  ↓
UniversalWorkQueue.ingest(packet)
  ├─ packet.status → CLASSIFIED
  ├─ packet.status → PLANNED
  ├─ packet.status → READY_FOR_REVIEW
  └─ packet.status → APPROVAL_PENDING
  ↓
PolicyEngine.evaluate(risk_class=medium)
  ├─ Verdict: APPROVE_AUTONOMOUSLY
  │  └─ packet.status → APPROVED
  │
  ├─ Verdict: REQUIRE_OPERATOR_APPROVAL
  │  └─ packet.status → APPROVAL_PENDING
  │     ↓
  │     OperatorApprovalGate.request()
  │     ↓
  │     [Cockpit shows approval panel]
  │     ↓
  │     operator approves
  │     └─ packet.status → APPROVED
  │
  └─ Verdict: DENY (high risk)
     └─ packet.status → BLOCKED
        ↓
        [Return to operator: "blocked, why"]

packet.status → DELEGATED
  ↓
ExecutionCoordinator.enqueue(plan)
  ↓
[Executor waits for dequeue]
  ↓
ApprovalIntercept (if HIGH risk)
  ├─ Request operator decision
  ├─ Executor thread waits on Event
  └─ Operator approves/rejects via cockpit
  ↓
TargetExecutor.execute(packet)
  ├─ WorkstationExecutor: subprocess, worktree, files
  ├─ AgentExecutor: Claude Code CLI
  └─ Other: VPS, Docker, Browser, Discord
  ↓
ExecutionProof(stdout, stderr, exit_code, duration_ms)
  ↓
packet.status → VALIDATING
  ├─ Validation plan runs
  ├─ Rollback plan staged (not executed unless needed)
  └─ verification_results collected
  ↓
packet.status → COMPLETED (if verified)
  ↓
CanonicalWritePath.update(memory)
  ├─ Template registry updated
  ├─ Agent reliability scored
  └─ Memory snapshots created
  ↓
EventSpine.emit(WORK_COMPLETED, proof_ids=[...])
  ↓
[Return to operator: execution complete, proof artifacts available]
```

**Duration:** 1s–minutes (depends on work)

---

### 9.3 Organism Loop (Full Cycle)
```
user_intent
  ↓
OrganismLoopEngine.execute_intent()
  │
  ├─ Step 1: EmpireRouter.get_reality_snapshot()
  │  └─ Current system state captured
  │
  ├─ Step 2: WorkPacketEngine.create_packet_from_intent()
  │  └─ WorkPacket(packet_id, ..., status=DRAFTED)
  │
  ├─ Step 3: UniversalWorkQueue.ingest_work_packet()
  │  └─ Packet lifecycle starts (DRAFTED → CLASSIFIED → ... → APPROVAL_PENDING)
  │
  ├─ Step 4: PolicyEngine.evaluate(risk_class)
  │  └─ Governance verdict: APPROVE_AUTONOMOUSLY | REQUIRE_APPROVAL | DENY
  │
  ├─ Step 5: WorkPacketExecutor.execute(packet) [if approved]
  │  ├─ Select target executor
  │  ├─ ApprovalIntercept (if HIGH/CRITICAL)
  │  ├─ Execute (subprocess, agent, etc.)
  │  └─ Proof artifact collected
  │
  ├─ Step 6: CanonicalWritePath.update(memory)
  │  ├─ Memory write receipt created
  │  └─ Learning signals recorded
  │
  ├─ Step 7: Packet status update
  │  └─ packet.status → COMPLETED (or FAILED)
  │
  └─ Step 8: EventSpine.emit(lifecycle_events)
     └─ Events published
  ↓
OrganismLoopResult(
  result_id, reality_snapshot_id, work_packet_id, governance_decision_id,
  execution_bundle_id, proof_artifact_ids, memory_write_receipt_id,
  event_ids, steps_completed, total_duration_ms, final_status, error
)
  ↓
[Complete result with all artifact IDs; operator can inspect any step]
```

---

## SECTION 10: GOVERNANCE DECISION TREE

### 10.1 Pre-Execution Gates (Deterministic Sequence)
```
operator_text
  ↓
1. IntentRouter.classify()
   → RouteType.WORK_PACKET?
   → YES: continue
   → NO (CONVERSATION): spine path
  ↓
2. IntentRuntime.detect_conflicts()
   → Active intent conflicts?
   → YES: block, explain conflict
   → NO: continue
  ↓
3. Risk classification (deterministic)
   → command/code pattern → risk_class
   → low | medium | high | critical
  ↓
4. PolicyEngine.evaluate(risk_class)
   → Approval required?
   → YES: ApprovalGate.request() OR ApprovalIntercept
   → NO: proceed
  ↓
5. Governance verdict (deterministic rules)
   → APPROVE_AUTONOMOUSLY
   → REQUIRE_OPERATOR_APPROVAL
   → DENY (safety violation)
  ↓
[if REQUIRE_OPERATOR_APPROVAL]
ApprovalGate holds candidate until operator decides
  ↓
[if DENY]
WorkPacket status → BLOCKED
[return to operator: why blocked]
  ↓
[if APPROVE_AUTONOMOUSLY]
WorkPacket status → APPROVED → DELEGATED
```

---

### 10.2 Executor-Level Gates (During Execution)
```
TargetExecutor.execute(packet)
  ↓
1. WorkstationExecutor.validate_path()
   → Path traversal attack?
   → YES: block
   → NO: continue
  ↓
2. WorkstationExecutor.classify_risk(command)
   → low | medium | high | critical
  ↓
3. [if HIGH/CRITICAL]
   ApprovalIntercept.request()
   ├─ Executor thread waits on Event
   ├─ Cockpit shows approval panel
   └─ Operator approves/rejects
  ↓
4. [if CPU overloaded]
   cpu_gate_check() → OVERLOADED?
   → YES: return None (skip execution, defer)
   → NO: continue
  ↓
5. Execute
  ↓
6. Post-execution validation
   → Did it work?
   → verification_passed?
```

---

## SECTION 11: SUBSYSTEM COMPOSITION FOR CAMPAIGN 2

### W2: Meta IDE & Coherence Feedback
**Composes:**
- IntentRouter (classify operator input)
- DevelopmentSessionBridge (observe code changes)
- IntentRuntime (track intents per session)
- WorkPacket (create fix packets from drift observations)
- ApprovalGate (hold auto-fixes for review)

**Emits:**
- Drift observations → WorkPackets
- Auto-fix candidates → approval panel

---

### W3: Autonomous Tick Loop & Cadence
**Composes:**
- IntentRouter (classify intent for work vs. conversation)
- StrategicGapEngine (detect gaps between goal and reality)
- UniversalWorkQueue (queue candidates)
- ApprovalGate (hold candidates for approval)
- PolicyEngine (governance evaluation)
- ExecutionCoordinator (if operator pre-approves)

**Emits:**
- Candidate supply → approval panel
- Approved candidates → execution queue

---

### W4: Autonomous Planning Loop
**Composes:**
- IntentRouter (classify intent)
- WorkPacketEngine (create packets)
- PolicyEngine (governance evaluation)
- ApprovalGate (hold plans for review)
- ExecutionSpine (planning stages 1–6, no execution)

**Emits:**
- Draft plans → approval panel
- Approved plans → W5 (no W4 execution, W5 owns execution)

---

### W5: Proof Loop & Multi-Agent Dispatch
**Composes:**
- IntentRouter (classify intent)
- OrganismLoopEngine (full 8-step cycle)
- ExecutionCoordinator (queue + dispatch)
- All executors (workstation, agent, vps, container, browser)
- ApprovalIntercept (runtime gating)
- CanonicalWritePath (memory updates)
- EventSpine (proof artifact emission)

**Emits:**
- Proof artifacts → operator verification
- Memory updates → system learning
- Lifecycle events → operator awareness

---

## SECTION 12: LINE COUNT AUDIT (Complete)

| Component | File | Lines |
|-----------|------|-------|
| ExecutionCoordinator | execution_coordinator.py | 1,179 |
| AgentExecutor | executors/agent_executor.py | 828 |
| WorkstationExecutor | executors/workstation_executor.py | 785 |
| ApprovalIntercept | executors/approval_intercept.py | 674 |
| OrganismLoopEngine | organism_loop.py | 497 |
| ExecutionSpine | execution/spine.py | 522 |
| IntentRuntime | operator/intent_runtime.py | 589 |
| WorkPacket | work_packet.py | 451 |
| ControlPlaneGovernance | control_plane/governance.py | 278 |
| ApprovalGate | approval_gate.py | 276 |
| IntentRouter (Operator) | operator/intent_router.py | 249 |
| DevelopmentSessionBridge | development_session_bridge.py | 353 |
| IntentRouter (Control Plane) | control_plane/router/intent_router.py | 170 |
| ApprovalStore | approval_store.py | 107 |
| **TOTAL** | | **6,915** |

---

## SECTION 13: CRITICAL GOTCHAS FOR W2–W5

1. **Intent Router Confidence:** Patterns score 0.80+, LLM refinement needed for ambiguous intents (0.45–0.75)

2. **Work Packet Lifecycle:** Transitions are deterministic; attempting invalid transition raises error. Test with `_VALID_TRANSITIONS`.

3. **Approval Intercept Threading:** Executor thread blocks on `Event`. Timeout defaults to 900s; operator must approve/reject or wait expires. No restart needed.

4. **Risk Classification:** Must be deterministic (no LLM calls). Patterns in WorkstationExecutor + AgentExecutor; fallback to `medium` if ambiguous.

5. **Governance Verdict:** PolicyEngine returns APPROVE_AUTONOMOUSLY | REQUIRE_OPERATOR_APPROVAL | DENY. Must handle all three paths.

6. **Executor Selection:** ExecutionCoordinator.seed_defaults() registers 7 executors. Custom executors must be registered before dispatch.

7. **Memory Write:** CanonicalWritePath must be composed into OrganismLoopEngine or called after execution manually.

8. **Event Spine:** All major state transitions should emit events; use `EventSpine.emit()` with domain + event_type for cockpit visibility.

9. **CPU Gate:** gated_subprocess_run() returns None if overloaded; must handle gracefully (defer work, don't crash).

10. **Instance Context:** All UMH code is multi-tenant; use runtime config (BIS) for AI name, founder names, ventures, etc. Never hardcode.

---

