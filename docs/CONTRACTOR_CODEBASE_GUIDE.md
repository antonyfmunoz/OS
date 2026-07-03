# UMH Codebase Guide — Complete Contractor Reference

> Generated 2026-07-03 from graphify AST index (42,603 source nodes, 40,613 edges, 2,979 files)
> Platform v1.0.0 — Production Certified, Frozen 2026-07-01

This document covers **every file and directory** in the /opt/OS repository.
It is organized in two parts: Part A explains architecture, conventions, and
development workflow; Part B is the exhaustive file-by-file reference.

---

# PART A — ARCHITECTURE & CONVENTIONS

## 1. What This System Is

UMH (Universal Mastery Hierarchy) is a production AI intelligence substrate — a modular platform that receives signals from any source (Discord, HTTP, scheduled events, mesh nodes), routes them through an 8-stage execution pipeline with governance checks, and produces responses using a multi-provider LLM chain with deterministic fallbacks.

It is NOT a chatbot framework. It is an operating system for running AI-augmented business operations.

**Current state:** Single-user validation phase. One organization, multiple ventures. Solo founder + contractor team. Deployed on a Hostinger VPS (orchestrator) with a Windows workstation (executor) connected via Tailscale.

**Tech stack:**
- Backend: Python 3.12 (host), Python 3.11 (Docker containers — no 3.12+ syntax in containerized code)
- Frontend: TypeScript, React 18, Vite, Tailwind CSS, shadcn/ui (Electron + PWA cockpit)
- API: Express + Drizzle ORM (TypeScript HTTP layer), FastAPI (Python operator API)
- Database: Neon Postgres with RLS
- LLM: Claude Opus 4.6 (primary via cc_sdk), Gemini 2.5 Flash, Groq, Ollama (fallback chain)

---

## 2. Architecture — The 4 Layers

Dependency direction is **strictly one-way downward**. Pre-commit hooks enforce this. Violating it blocks your commit.

```
┌─────────────────────────────────────────────────────┐
│  projections/  (EOS, CreatorOS, LyfeOS)             │
│  saas/         (EOS-specific routes, schema, seeds) │
├─────────────────────────────────────────────────────┤
│  transports/   (Discord, HTTP API, node mesh)       │  ← I/O surfaces
├─────────────────────────────────────────────────────┤
│  adapters/     (LLM routing, browser, calendar)     │  ← external integrations
├─────────────────────────────────────────────────────┤
│  substrate/    (types, execution, governance, state) │  ← universal platform
└─────────────────────────────────────────────────────┘
         ▲ imports flow DOWN only, never up
```

**How substrate talks to upper layers without importing them:**
`substrate/sockets/` provides abstract ports. The transport layer registers a concrete implementation at startup. Substrate calls the thin wrapper — never importing from transports directly.

```python
# substrate/sockets/channel_port.py — example abstract port
_router_fn = None

def register_channel_router(fn):
    global _router_fn
    _router_fn = fn

def get_channel_router():
    if _router_fn:
        return _router_fn()
    return None
```

---

## 3. The Two Core Flows

### 3a. Signal Execution (read path)

Everything enters the substrate as a `SignalEnvelope`:

```python
class SignalEnvelope(BaseModel):
    id: UUID
    source: SignalSource          # user, system, scheduled, adapter, organism
    urgency: SignalUrgency        # immediate, high, normal, low, background
    modality: Modality            # text, voice, image, multimodal
    content: str
    user_id: str
    organization_id: str
    venture_id: str | None
    authority_tier: int           # 1-9, governs what actions are allowed
    attachments: list[Attachment]
    metadata: dict[str, Any]
```

The `Substrate` class is the single entry point, composing 9 subsystems:

```python
class Substrate:
    def __init__(self):
        self.self_model = self_model
        self.identity = ConcreteIdentityResolver()
        self.governance = ConcreteGovernanceEngine()
        self.memory = ConcreteMemorySystem()
        self.context = ConcreteContextAssembler(memory_system=self.memory)
        self.registry = ConcreteComponentRegistry()
        self.trace = ConcreteTraceRecorder()
        self.feedback = ConcreteFeedbackCapture()
        self.spine = ConcreteExecutionSpine(...)
        self.router = ConcreteSignalRouter(...)
```

The **ExecutionSpine** runs 8 stages:

```
interpret → recall → lookup → compose → route → execute → trace → feedback
```

Deterministic-first: intent classification uses regex patterns before any LLM call. If all providers fail, the spine returns a heuristic response.

### 3b. Governed Mutation (write path)

Every state change routes through `governed_mutation()`. No exceptions.

```
Propose → Governance Check → Approve/Reject → Execute → Verify → Learn → Journal → Event
```

Core types: `ActionEnvelope`, `MutationRequest`, `MutationResponse`, `MutationSpec`, `MutationRegistry`.

---

## 4. Intelligence Routing

All LLM calls go through one entry point:

```python
from adapters.models.model_router import call_with_fallback

result = call_with_fallback(prompt="...", task_type=TaskType.ANALYSIS)
```

**Routing chain:** cc_sdk (Opus 4.6 via Claude Code subscription, free) → Gemini 2.5 Flash → Groq → Ollama

- `cc_sdk` reads OAuth token from the ancestor Claude Code process via `/proc`
- CEO/strategic agents force best model: `agent_type='ceo'` or `force_opus=True`
- Every LLM call has a deterministic fallback with regex-based intent matching

Never call providers directly. Never hardcode `anthropic.Anthropic()`. Always `call_with_fallback()`.

---

## 5. Docker Services

6 containerized services on a shared `eos_network` bridge. All mount `/opt/OS` as `/app`, use Python 3.11-slim, share `services/.env` + `infra/docker/umh.env`.

| Container | Entrypoint | Port | CPU/Mem | Purpose |
|-----------|-----------|------|---------|---------|
| `os-discord` | `python3 services/discord_bot.py` | 8765 | 0.35/1G | Primary Discord bot |
| `os-operator` | `uvicorn services.operator_api:app` | 8091 | 0.50/512M | FastAPI HTTP API |
| `os-webhook` | `python3 transports/api/webhooks/calendly_webhook.py` | 8080 | 0.25/128M | Calendly webhook |
| `os-scraper` | `python3 services/overnight_scrape.py` | — | 0.25/256M | Batch scraping |
| `os-browser` | `python3 services/browser_relay.py` | 8086 | 0.50/1.28G | Browser automation |
| `os-livekit` | `livekit-server` | 7880 | 0.35/256M | Voice/video |

**Restart a service:** `docker restart os-discord` (use container name, not compose service name)

---

## 6. The 9 Laws (Non-Negotiable)

Each law exists because it was violated and caused a real incident. Pre-commit hooks enforce most.

### Law 1: CPU Gate
Never use raw `subprocess.run/Popen/call` in substrate/, adapters/, transports/, or services/. Use `gated_subprocess_run()` from `substrate/execution/cpu_gate.py`. Enforced by `scripts/check_cpu_gate.py`.

### Law 2: Cockpit Deploy Gate
Never run `flyctl deploy` directly. Always `bash cockpit/deploy.sh`.

### Law 3: Python 3.11 in Docker
No Python 3.12+ syntax in containerized code.

### Law 4: Dependency Direction
substrate/ never imports from transports/ or services/. Enforced by `scripts/check_dependency_direction.py`.

### Law 5: Type Coherence
Check `substrate/canonical_types.py` before defining any new type. Enforced by `scripts/check_type_divergence.py`.

### Law 6: Instance Context
No hardcoded user/AI/company names in substrate/. Enforced by `scripts/check_instance_leak.py`.

### Law 7: Projection Boundary
Substrate is universal. Projection-specific code stays in projections/. Enforced by `scripts/check_projection_leak.py`.

### Law 8: Credential Injection
All credentials flow through 1Password `op run`. Enforced by `scripts/check_credential_injection.py`.

### Law 9: Deterministic-First
Every LLM call MUST have a deterministic fallback. "All providers down — does it still work?" Must be yes.

---

## 7. Development Workflow

### Pre-Commit Hooks
- `scripts/check_cpu_gate.py` — blocks raw subprocess calls
- `scripts/check_dependency_direction.py` — blocks upward imports
- `scripts/check_type_divergence.py` — blocks duplicate type definitions
- `scripts/check_projection_leak.py` — blocks projection names in substrate
- `scripts/check_instance_leak.py` — blocks hardcoded instance context
- `scripts/check_credential_injection.py` — blocks plaintext credentials
- `scripts/check_secret_patterns.py` — blocks committed secrets
- `scripts/check_ungoverned_mutations.py` — blocks ungoverned mutation endpoints

### Testing
```bash
python3 -m pytest tests/                    # full suite
python3 -m pytest tests/substrate/          # substrate tests only
python3 -m pytest tests/ -k "test_spine"    # pattern match
```

### Import Verification
```bash
python3 -c "from substrate.types import SignalEnvelope; print('ok')"
```

### Service Restart
```bash
docker restart os-discord     # restart the Discord bot
docker restart os-operator    # restart the API
```

### Cockpit Deploy
```bash
bash cockpit/deploy.sh        # ALWAYS this, NEVER raw flyctl
```

---

## 8. Infrastructure

- **VPS** (`srv1500858`) — Hostinger, lightweight orchestrator only
- **Beast** (`antonys beast pc`) — Windows workstation, GPU, heavy compute
- Connected via Tailscale private network
- Device names from `infra/device_registry.json` — never hardcode raw strings

---

## 9. Top 30 Most-Connected Symbols

These are the architectural spine — the most heavily referenced symbols in the codebase. If you change any of these, you are touching critical infrastructure.

| Edges | Symbol | File |
|-------|--------|------|
| 155 | organism_bridge.py | transports/api/organism_bridge.py |
| 111 | cockpit.py | transports/api/cockpit.py |
| 110 | cockpit_rooms_routes.py | transports/api/cockpit_rooms_routes.py |
| 94 | types.py | substrate/types.py |
| 92 | VisionWsClient | cockpit/src/renderer/api/vision-ws.ts |
| 70 | OrganismDaemon | substrate/organism/daemon.py |
| 57 | TestIndividualArtifactExistence | tests/test_phase14_6b_umh_code_resolved_canon.py |
| 56 | cockpit_operator_loop_ext_routes.py | transports/api/cockpit_operator_loop_ext_routes.py |
| 52 | OrchestratorKernel | substrate/organism/orchestrator_kernel.py |
| 50 | test_agent_executor.py | tests/test_agent_executor.py |
| 47 | cockpit_organism_routes.py | transports/api/cockpit_organism_routes.py |
| 46 | cockpit_operator_loop_session_routes.py | transports/api/cockpit_operator_loop_session_routes.py |
| 46 | cockpit_operator_loop_routes.py | transports/api/cockpit_operator_loop_routes.py |
| 45 | ContinuityEngine | substrate/workstation/continuity_engine.py |
| 44 | orchestrator.py | substrate/control_plane/orchestrator/orchestrator.py |
| 43 | cockpit_spine_router.py | transports/api/cockpit_spine_router.py |
| 42 | ExecutivePortfolioRuntime | substrate/organism/executive_portfolio_runtime.py |
| 41 | tables.py | projections/lyfeos/integration/tables.py |
| 41 | c29_benchmark.py | tests/certification/c29_benchmark.py |
| 40 | CameraAdapter | nodes/windows/umh_node/adapters/camera.py |
| 39 | NodeMeshServer | transports/node_mesh/server.py |
| 38 | WorkPacketEngine | substrate/organism/work_packet_engine.py |
| 38 | ResourceAllocationRuntime | substrate/organism/resource_allocation_runtime.py |
| 37 | AdvisorConversation | substrate/organism/advisor_conversation.py |

---

# PART B — FILE-BY-FILE REFERENCE

Every source file in the repository, organized by directory. Each file gets a one-line description explaining what it does.

---

## B1. substrate/ — Universal Platform (986 Python files)

The substrate is the core of UMH. It contains the type system, execution pipeline, governance engine, organism runtime, and all universal mechanisms. Nothing in substrate/ is specific to any particular projection (EOS, CreatorOS, etc.).

### substrate/ root files

| File | Purpose |
|------|---------|
| `__init__.py` | `Substrate` class — THE single entry point. Composes 9 subsystems (self_model, identity, governance, memory, context, registry, trace, feedback, spine) + router |
| `types.py` | THE type system — SignalEnvelope, SignalSource, SignalUrgency, Modality, RiskClass, CapabilityStatus, Attachment, ~30 Pydantic models |
| `canonical_types.py` | Registry of ~80 canonical types — check here FIRST before defining any new type |
| `self_model.py` | System self-model — the substrate's awareness of its own structure and state |

### substrate/organism/ — The Autonomous Agent Society (274 root files + 5 subdirectories)

The largest directory in the codebase. Contains the organism runtime — the autonomous agent society that runs on top of the substrate. Handles work packets, agent coordination, governance, and self-improvement.

| File | Purpose |
|------|---------|
| `action_bridge.py` | Governed composition of catalog, observation, and execution |
| `action_catalog.py` | Data-driven registry of governed operator actions |
| `action_envelope.py` | ActionEnvelope — canonical executable object for ALL organism mutations |
| `action_voice_contract.py` | Interface between intent sources and ActionBridge |
| `advisor.py` | Advisor cell — top-level orchestrator of the organism |
| `advisor_conversation.py` | Multi-turn conversation with intent routing (37 edges) |
| `advisor_hierarchy.py` | Governed recursive advisory orchestration |
| `advisor_reconciliation.py` | Detects reconciliation intent in operator input |
| `agent_capability_model.py` | Track agent reliability per capability |
| `agent_execution_runner.py` | Invokes coding agents inside governed sandboxes |
| `agent_fleet_runtime.py` | Unified agent coordination layer |
| `agent_registry.py` | Agent types, capabilities, permissions, and routing |
| `agent_runtime.py` | Foundational behavior of every agent in the society |
| `agents.py` | Concrete agent cells — Researcher, Builder, AutoResearch |
| `allocation_loop.py` | Governed runtime allocation loop — continuous leverage allocator |
| `approval_gate.py` | Requires explicit approval before sandbox execution |
| `approval_store.py` | JSONL persistence for governance-blocked signals |
| `artifact_registry.py` | Indexes produced outputs across UMH |
| `assisted_executor.py` | Governed execution of approved maintenance actions |
| `assumption_tracking_runtime.py` | Governed assumption records |
| `async_coordinator.py` | Event-driven objective lifecycle |
| `automation_pipeline.py` | Promote repeated interventions to automation |
| `autonomous_action_gateway.py` | Structural enforcement of spine-routed mutation |
| `autonomous_cadence.py` | Scheduled autonomous improvement discovery |
| `autonomous_improvement_lane.py` | Bounded autonomous LOW-risk self-improvement |
| `autonomous_pr_factory.py` | Converts eligible improvements into isolated PRs |
| `autonomous_tick.py` | Continuous organism metabolism heartbeat |
| `benchmark_harness.py` | Measures Pipeline A (legacy) vs Pipeline B (governed) |
| `bottleneck_engine.py` | Organism operational self-optimization |
| `candidate_supply_engine.py` | Discovers improvement candidates from real organism sources |
| `canonical_update.py` | Proposed changes to canonical truth |
| `capability_compounding_runtime.py` | Capability compounding (C22.4) |
| `capability_evolution_engine.py` | Capability evolution tracking |
| `capability_gap_engine.py` | Detect missing/immature capabilities for goals |
| `capability_graph_engine.py` | Dependency/composition edges between capabilities |
| `capability_portfolio_runtime.py` | Portfolio-level health and compounding metrics |
| `capability_runtime.py` | Emergent capability tracking and maturity lifecycle |
| `capability_validation_runtime.py` | Benchmark storage, reporting, freshness tracking |
| `change_event.py` | State change model for propagation planning |
| `changeset_manifest.py` | Evidence record for every autonomous branch/PR |
| `claude_code_runtime_adapter.py` | Claude Code PTY runtime adapter skeleton |
| `coherence_propagation.py` | Parallel dependent-system updates on verified change |
| `command_runtime.py` | Canonical intent-to-action layer for all operator surfaces |
| `composition_engine.py` | Deterministic intent to plan from observed capabilities |
| `compounding_engine.py` | Turn internal learning into leverage |
| `compute_fabric_runtime.py` | Unified compute body map |
| `context_diagnostic.py` | Models for diagnostic reports on context state |
| `context_ingestion_engine.py` | Ingest local/system context sources |
| `context_resolution.py` | "The system already knows" layer |
| `continuity_runtime.py` | Operational continuity engine |
| `continuous_qualification.py` | Daemon tick stage for live ORL measurement |
| `contradiction_engine.py` | Detect mismatches between declared and observed reality |
| `coordinator.py` | Hierarchical task decomposition and runtime assignment |
| `correspondence_scheduler.py` | Periodic drift detection for projections |
| `council.py` | Multi-perspective advisory layer |
| `cross_source_reconciler.py` | Detect relationships across fragmented sources |
| `daemon.py` | OrganismDaemon — manages agent lifecycle (70 edges, top-10 symbol) |
| `daily_driver_log.py` | Records unhandled failures during real operation |
| `decision_impact_engine.py` | Blast radius analysis for strategic decisions |
| `decision_lineage_engine.py` | Causal chain traversal for strategic decisions |
| `decision_registry.py` | First-class strategic decision records |
| `decision_validity_engine.py` | Evaluates whether decisions still make sense |
| `delegation_followup.py` | Checks overdue delegations and acts |
| `delegation_readiness_runtime.py` | Pre-assignment feasibility + outcome prediction |
| `delegation_runtime.py` | Intent classification, delegation proposals, mission lifecycle |
| `delegation_topology.py` | Chooses execution structure for a work packet |
| `dependency_graph.py` | Subsystem dependency model |
| `deploy_verification_worker.py` | No human should discover a white screen |
| `dev_session_tracker.py` | Wraps dev sessions as governed spine executions |
| `development_session_bridge.py` | Makes coding agents governed organs of the organism |
| `device_awareness.py` | Deterministic device detection and capability routing |
| `device_capacity.py` | Per-device worker slots and backpressure |
| `device_provisioner.py` | Multi-OS diagnosis + role-based provisioning |
| `device_registry_writer.py` | Atomic writes + cache invalidation |
| `device_role_registry.py` | Tracks device roles and capabilities |
| `dex_conversation.py` | Backward-compat shim to advisor_conversation.py |
| `dex_reconciliation.py` | Backward-compat shim to advisor_reconciliation.py |
| `diagnostic_engine.py` | Analyze ingested context for canonical truth state |
| `distributed_runtime.py` | Facade composing all distributed runtime subsystems |
| `documentation_awareness_runtime.py` | Content-level metadata for docs |
| `domain_registry.py` | First-class domain definitions for the Empire WorkPacket Engine |
| `drift_detection_engine.py` | Unified drift synthesis |
| `embodiment_runtime.py` | Natural language intent becomes governed work |
| `empire_router.py` | Routes founder intent to domain-classified governed WorkPackets |
| `environment_discovery.py` | Device, filesystem, application, account inventory |
| `environment_graph.py` | Continuously updated operational world-state |
| `environment_reconciler.py` | Continuous drift correction |
| `event_spine.py` | Canonical organism-level event transport |
| `execution_coordinator.py` | Canonical orchestration layer (Phase 13) |
| `execution_economy.py` | Runtime cost/value tracking and leverage scoring |
| `execution_graph.py` | Evidence-grade lineage validation |
| `execution_journal.py` | Append-only execution ledger for all organism mutations |
| `execution_ledger.py` | Canonical record of every execution request and outcome |
| `execution_lifecycle_runtime.py` | Campaign 16.2 runtime |
| `execution_modes.py` | Governed transition from observation to action |
| `executive_brief_runtime.py` | Structured operator briefing synthesis |
| `executive_portfolio_runtime.py` | Executive portfolio (42 edges, top-20 symbol) |
| `executor_runtime.py` | Canonical execution contract layer (Phase 14) |
| `goal_alignment_engine.py` | Ensure work supports goals |
| `goal_drift_engine.py` | Detect movement away from objectives |
| `goal_hierarchy_engine.py` | Structural operations on the goal tree |
| `governance_runtime.py` | Governance Runtime (C15.0) |
| `governed_execution_runtime.py` | Governed Execution Runtime (C16.0) |
| `governed_spine.py` | GovernedExecutionSpine — THE single mutation gateway |
| `governed_work_runtime.py` | MANDATORY execution gateway |
| `grounded_handlers.py` | Deterministic answers backed by real data |
| `grounding_registry.py` | Source data requirements for deterministic status answers |
| `handoff.py` | Structured agent-to-agent task transfer |
| `homeostasis.py` | The organism's immune/self-regulation system |
| `impact_analyzer.py` | Computes change impact across the propagation graph |
| `infrastructure_runtime.py` | Register and track system and institutional infrastructure |
| `ingestion_job.py` | Tracks context ingestion work units |
| `institutional_memory_runtime.py` | Institutional Memory (C15.2) |
| `intent_classifier.py` | Converts raw user intent into structured classification |
| `knowledge_awareness_runtime.py` | Meaning, not just documents |
| `knowledge_model_registry.py` | System knowledge containers |
| `learning_extraction_runtime.py` | Learning extraction |
| `learning_portfolio_runtime.py` | Learning portfolio |
| `leverage_assimilation.py` | Ingest, classify, and operationalize external leverage |
| `leverage_engine.py` | Determines highest-impact actions |
| `leverage_metrics.py` | Measures actual organism value |
| `maintenance_loop.py` | OBSERVE-mode infrastructure health cycle |
| `memory_promotion.py` | Governed promotion from instance to canonical memory |
| `mesh_reconciler.py` | Syncs RuntimeGraph with live mesh relay |
| `meta_ide_runtime.py` | Unified development surface |
| `mission.py` | Bridge between user conversation and organism execution |
| `mutation_catalog.py` | Maps HTTP endpoints to MutationSpec names |
| `mutation_registry.py` | Canonical registry of executable mutation types |
| `mutation_router.py` | Canonical choke point for all organism state mutations |
| `next_action_engine.py` | Evidence-based action recommender |
| `objective_physics.py` | Causal execution dynamics |
| `objective_queue.py` | Continuous objective intake for OrganismCoordinator |
| `observability.py` | Unified dashboard snapshot |
| `operating_loop_coherence_runtime.py` | Aggregation, reporting, coherence synthesis |
| `operational_truth.py` | Scoreboard for UMH operational reality |
| `operationalization_runtime.py` | Link capabilities to reusable artifacts |
| `operator_acceptance.py` | End-to-end acceptance test tracking |
| `operator_acceptance_mode.py` | Standard vs deterministic-only vs blocked mode |
| `operator_acceptance_scenarios.py` | Predefined end-to-end test scenarios |
| `operator_compression.py` | Reduce human operational burden |
| `operator_escape_tracker.py` | Records exits from UMH organism |
| `operator_loop_coordinator.py` | Orchestrates end-to-end acceptance loop |
| `operator_loop_runtime.py` | The Jarvis Runtime |
| `operator_migration_runtime.py` | Track and close external-loop dependencies |
| `operator_readiness_gate.py` | Phase 13.4 readiness assessment |
| `operator_response.py` | Structured response contract for orchestrator kernel |
| `operator_session.py` | Conversational state for operator-orchestrator interaction |
| `orchestration_loop.py` | Persistent autonomous execution |
| `orchestrator_awareness_runtime.py` | Synthesized reality model for the orchestrator |
| `orchestrator_kernel.py` | Central intelligence routing (52 edges, top-10 symbol) |
| `organism_coordination_engine.py` | Organism Coordination (C15.1) |
| `organism_loop.py` | Convergence coordinator for organism execution |
| `organism_portfolio_runtime.py` | Organism Portfolio (C15.3) |
| `organism_state_runtime.py` | Organism State Runtime (C16.1) |
| `outcome_learning.py` | Learn from execution outcomes |
| `outcome_pattern_engine.py` | Outcome pattern detection |
| `outcome_tracking_runtime.py` | Measure progress toward goals |
| `outcome_verification.py` | Replaces 'Task Complete' with 'Outcome Verified' |
| `packet_router.py` | Capability-first work routing |
| `parallel.py` | Run multiple agents concurrently |
| `permission_dialogue.py` | Ask before expanding context access |
| `plan_execution_adapter.py` | Bridges CompositionPlan to GovernedExecutionSpine |
| `prediction_portfolio_runtime.py` | Prediction portfolio |
| `presence_runtime.py` | Operator presence awareness |
| `priority_engine.py` | Deterministic priority synthesis |
| `product_factory_runtime.py` | Product Factory (C22.5) |
| `production_merge_verifier.py` | Confirms sandboxed PR became production truth |
| `production_ops_runtime.py` | Production Operations (C22.0) |
| `production_planning_runtime.py` | Production Planning (C22.1) |
| `production_review_runtime.py` | Production Review (C22.3) |
| `production_truth_delta.py` | What actually changed in production after merge |
| `production_workforce_runtime.py` | Production Workforce (C22.2) |
| `profile_runtime.py` | Canonical authority for operator work identity |
| `project_registry.py` | First-class project entities |
| `projection_certification.py` | Graduated L0-L5 certification |
| `projection_engine.py` | Predictive world-model layer |
| `projection_integration_runtime.py` | Audit/mapping layer over projections |
| `projection_port.py` | Projection-agnostic organism state port |
| `projection_readiness_gate.py` | Blocks build until source reconciliation is sufficient |
| `projection_reconciliation_engine.py` | Diagnoses divergence across projection sources |
| `projection_source_registry.py` | Tracks sources per projection for reconciliation |
| `promotion_threshold_policy.py` | Governs cadence mode transitions |
| `proof_runtime.py` | Complete proof packages per execution |
| `proof_store.py` | JSONL persistence for proof packages |
| `propagation_executor.py` | Executes propagation plans in dry-run or governed mode |
| `propagation_graph.py` | Dependency-aware change propagation model |
| `propagation_graph_builder.py` | Extracts nodes and edges from real system state |
| `propagation_planner.py` | Creates wave-based propagation plans |
| `propagation_wiring.py` | Registers all propagation targets with the engine |
| `protocols.py` | Typed contracts for the agent society |
| `qualification_harness.py` | Organism qualification harness |
| `readiness_model.py` | 6-dimension readiness assessment |
| `reality_graph.py` | Canonical operator-world graph |
| `recommendation_engine.py` | Unified action recommendation synthesis |
| `reconciliation_engine.py` | Structured context reconciliation sessions |
| `reconciliation_session.py` | Structured operator-AI context alignment |
| `recursion_governance.py` | Bounded recursive execution control |
| `reliability_signals.py` | Normalizes production-backed signals for cadence ranking |
| `reliability_weighted_ranker.py` | Deterministic candidate ranking using production signals |
| `report_dispatcher.py` | Sends task completion reports to Discord + cockpit chat |
| `repository_awareness_runtime.py` | File-level depth for repositories |
| `resource_allocation_runtime.py` | Resource Allocation (C14.0, 38 edges) |
| `risk_engine.py` | Unified risk register synthesis |
| `roadmap_engine.py` | Phase linkage model for self-build queue |
| `role_contracts.py` | Template-based role definitions |
| `runtime_adapter.py` | Abstract contract for execution surfaces |
| `runtime_adapters.py` | Concrete RuntimeAdapter implementations |
| `runtime_awareness_runtime.py` | Unified view of active system state |
| `runtime_fleet.py` | Tracks available runtime providers and selection decisions |
| `runtime_graph.py` | Canonical runtime registry with dynamic availability |
| `runtime_handoff.py` | Bridges Work Packets to runtime sessions |
| `runtime_manager.py` | Orchestrates governed runtime session lifecycle |
| `runtime_session.py` | Governed execution surface for workcell runtimes |
| `runtime_state_registry.py` | Live environment awareness for the workstation |
| `runtime_supervisor.py` | Persistent runtime lifecycle management |
| `sandbox_orchestrator.py` | Ties approval gate to PR factory execution |
| `scenario_intelligence_engine.py` | Scenario intelligence |
| `self_build_queue.py` | Canonical work item model and queue engine |
| `self_maintenance_bridge.py` | Wires degradation detection to work packet creation |
| `self_model_predictor.py` | Statistical self-prediction engine (Welford variance) |
| `service_dependency_graph.py` | Canonical service dependency models |
| `service_dependency_registry.py` | Canonical registry of service dependencies |
| `service_failure_engine.py` | Computes failure impact across service graph |
| `session_runtime.py` | Canonical session architecture |
| `shell_runtime_adapter.py` | Safe subprocess execution surface |
| `slo_definitions.py` | Concrete operational targets |
| `source_registry.py` | Tracks all context sources available to UMH |
| `source_truth_linker.py` | Cross-domain edge builder for the Reality Graph |
| `source_truth_runtime.py` | Full organizational lineage (C22.6) |
| `spine_guard.py` | Enforcement layer for the single-spine mutation doctrine |
| `state_authority_graph.py` | Canonical state domain authority models |
| `state_coherence_engine.py` | Detects state authority coherence across nodes |
| `state_registry.py` | Canonical registry of state domain authorities |
| `store.py` | JSONL persistence for deliverables, messages, agent state |
| `strategic_context_runtime.py` | Unified executive synthesis facade |
| `strategic_gap_engine.py` | Compares reality to target goals, produces gaps |
| `strategic_memory_engine.py` | Institutional memory with timeline and replay |
| `strategic_planning_engine.py` | Generate plans linking current reality to goals |
| `strategic_tick_loop.py` | Continuous governed awareness engine |
| `sync_policy.py` | How UMH relates to external tools |
| `system_identity.py` | Canonical UMH identity |
| `tailscale_discovery.py` | Diffs tailscale peers vs device registry |
| `template_governance.py` | 9-dimension scoring for template cadence eligibility |
| `template_registry.py` | Reusable executable structures from governed execution |
| `template_seeder.py` | Seeds evidence-backed templates to the runtime store |
| `tradeoff_intelligence_engine.py` | Tradeoff Intelligence (C14.1) |
| `trajectory_intelligence_runtime.py` | Trajectory intelligence |
| `trial_runner.py` | Self-improvement reliability trial runner |
| `trust_score.py` | Composite trust scoring via weakest-link gate |
| `umh_node_registry.py` | Canonical registry of UMH organism nodes |
| `umh_node_topology.py` | Canonical node role and version models |
| `umh_version_coherence.py` | Detects version drift across nodes |
| `universal_work_queue.py` | Canonical queue for all work packets |
| `work_graph.py` | Read-only query projection over existing work stores |
| `work_packet.py` | Canonical intent-to-execution container |
| `work_packet_engine.py` | Creates work packets from user intent (38 edges) |
| `work_portfolio_runtime.py` | Execution health, velocity, drift detection |
| `work_readiness_runtime.py` | Multi-dimensional readiness classification |
| `work_recovery_runtime.py` | Maps work states to recovery actions |
| `workcell.py` | Planning/delegation workcell model |
| `workcell_daemon.py` | Persistent processor for workcell inboxes |
| `workcell_protocol.py` | Durable inbox/outbox execution cells |
| `worker_cell.py` | Bounded task execution through existing pipeline |
| `worker_lifecycle.py` | Structured lifecycle events |
| `worker_registry.py` | Active worker inventory per device |
| `workload_placement_policy.py` | Selects correct runtime + device for Work Packets |
| `workload_probes.py` | Live operational pressure into the organism |
| `workload_runner.py` | Governed execution of operational jobs |
| `workspace_awareness.py` | Deterministic active-context detection |
| `workstation_runtime.py` | Canonical workstation planning layer (Phase 10) |
| `worktree_sandbox.py` | Isolated execution environments for autonomous improvements |
| `world_model.py` | Organism-level self-model of UMH system state |

#### substrate/organism/audits/ (7 files)

Audit and qualification tooling: `audit_harness.py`, `qualification_runner.py`, `regression_gate.py`, `slo_audit.py`, `health_audit.py`, `coverage_audit.py`, `drift_audit.py`.

#### substrate/organism/benchmarks/ (26 files)

Production and competitive benchmark runtimes: `competitive_benchmark.py`, `governed_benchmark.py`, `latency_benchmark.py`, `quality_benchmark.py`, `throughput_benchmark.py`, and 21 more benchmark modules.

#### substrate/organism/executors/ (5 files)

`governed_executor.py`, `sandbox_executor.py`, `shell_executor.py`, `worktree_executor.py`, `remote_executor.py`.

#### substrate/organism/self_use/ (7 files)

`self_use_catalog.py`, `gap_ledger.py`, `self_assessment.py`, `self_diagnosis.py`, `self_improvement.py`, `self_report.py`, `gap_report.py`.

#### substrate/organism/tests/ (69 files)

Organism-specific test fixtures: `conftest.py`, `test_advisor.py`, `test_daemon.py`, `test_delegation.py`, `test_governance.py`, `test_kernel.py`, `test_mutation.py`, `test_spine.py`, `test_work_packet.py`, and 60 more.

### substrate/execution/ — How Work Gets Done (166 files)

| File | Purpose |
|------|---------|
| `cpu_gate.py` | CPU Gate — `cpu_gate_check()`, `gated_subprocess_run()`, `gated_popen()` |
| `credential_gate.py` | Validates credentials flow through 1Password |
| `spine.py` | ExecutionSpine — 8-stage pipeline (interpret, recall, lookup, compose, route, execute, trace, feedback) |
| `trace.py` | TraceRecorder — records execution traces |
| `feedback.py` | FeedbackCapture — captures execution quality signals |
| `feedback_loop.py` | RLHF — explicit human feedback ingestion |
| `executor.py` | Work packet executor — governed execution pipeline |
| `pipeline.py` | ExecutionPipeline — master success loop |
| `mastery_gate.py` | Mandatory pipeline check before execution |
| `proof_generator.py` | Creates verifiable proof artifacts |
| `queue.py` | Priority-aware work packet queue |
| `understanding_bridge.py` | Wires understanding layer into execution pipeline |

#### substrate/execution/bridge/ (71 files)

Bridge layer connecting execution to transports. One bridge file per API route group.

#### substrate/execution/workers/ (44 files)

Worker implementations for every job type: analysis, browser, coding, content, data, deployment, document, email, engineering, financial, github, integration, marketing, monitoring, outreach, planning, research, review, scheduling, slack, voice, and 23 more.

#### substrate/execution/runtime/ (18 files)

`capability_router.py` (Capability enum with 28 job capabilities), `worker_runtime_contracts.py` (EnvironmentType, AuthorityDomain), `worker_pool.py`, `runtime_config.py`, and 14 more.

#### Other execution subdirectories

| Directory | Files | Purpose |
|-----------|-------|---------|
| `actuation/` | 5 | Physical action execution (mouse, keyboard, display) |
| `agents/` | 3 | Agent execution implementations |
| `loop/` | 4 | Persistent loop infrastructure |
| `voice/` | 3 | Voice processing pipeline |
| `media/` | 2 | Media processing |
| `adapters/` | 2 | Execution adapter interfaces |
| `ingestion/` | 1 | Ingestion pipeline |

### substrate/control_plane/ — Governance, Routing, Orchestration (77 files)

| File | Purpose |
|------|---------|
| `governance.py` | GovernanceEngine — THE single governance entry point |
| `memory.py` | MemorySystem — unified protocol over memory stores |
| `registry.py` | ComponentRegistry — unified registry for all substrate components |

#### Subdirectories

| Directory | Files | Purpose |
|-----------|-------|---------|
| `actions/` | 12 | Action definitions and handlers |
| `runtime/` | 13 | Control plane runtime implementations |
| `agents/` | 7 | Control plane agent coordination |
| `strategy/` | 5 | Strategic planning subsystem |
| `scheduling/` | 5 | Scheduling and cadence |
| `invariants/` | 4 | Invariant enforcement |
| `router/` | 4 | Signal routing |
| `context/` | 3 | Context management |
| `events/` | 3 | Event handling |
| `onboarding/` | 3 | System onboarding |
| `coordination/` | 2 | Multi-agent coordination |
| `delegation/` | 2 | Delegation management |
| `goals/` | 2 | Goal management |
| `identity/` | 2 | Identity resolution |
| `proactive/` | 2 | Proactive actions |
| `signals/` | 2 | Signal processing |

### substrate/workstation/ — Operator Workstation (56 files)

| File | Purpose |
|------|---------|
| `continuity_engine.py` | ContinuityEngine — 45 edges, top-20. Orchestrates all continuity |
| `activation.py` | Activation signal and presence session |
| `agent_workforce_runtime.py` | Agent Workforce Runtime (C19.1) |
| `ambient_wake_runtime.py` | Ambient Wake Runtime (C20.2) |
| `app_resolver.py` | Chrome-first browser policy, app vs website classification |
| `attention_aggregation_runtime.py` | Attention Aggregation (C18.2) |
| `attention_vision_runtime.py` | Attention Vision (C21.3) |
| `camera_commands.py` | Routes CAMERA_CONTROL intents to operations |
| `checkpoint.py` | State snapshot on continuity transitions |
| `cockpit_capability_map.py` | Audit surface for cockpit routes, panels, stores |
| `command_center_mvp_runtime.py` | Operator landing surface |
| `command_router.py` | Natural language command classification and routing |
| `continuity.py` | Unified lifecycle for operator presence/absence |
| `device_presence.py` | Device presence registry |
| `environment_awareness_runtime.py` | Environment Awareness (C21.1) |
| `execution_fabric_runtime.py` | Execution Fabric (C19.0) |
| `file_browser.py` | Safe read-only file browser |
| `intent_contract.py` | Converts operator intent into end-state designs |
| `lifecycle_modes.py` | System-level cycle governing safety and background behavior |
| `loop_engine.py` | End-state verification and progress reporting |
| `meta_ide_context_runtime.py` | Read-only context binding for the build surface |
| `meta_ide_projection_loop_runtime.py` | Governed build from inside cockpit |
| `mode_commands.py` | Mode switching via natural typed commands |
| `mode_resolver.py` | Authoritative composite of all mode systems |
| `mvp_readiness_runtime.py` | Objective MVP readiness scoring across 14 dimensions |
| `operating_loop_runtime.py` | Visibility layer over existing execution systems |
| `orchestrator_presence_runtime.py` | Persistent presence layer for primary orchestrator |
| `overnight_queue.py` | Overnight safe-work queue |
| `profile_behavior.py` | Per-profile policies for voice, camera, notifications |
| `profile_modes.py` | Operator activity context governing workspace/tool selection |
| `resume_brief.py` | "What happened while I was gone?" |
| `screen_awareness_runtime.py` | Screen Awareness (C21.0) |
| `security_mode.py` | Governed security posture for the cockpit |
| `session_machine_runtime.py` | Session Machine (C19.2) |
| `state.py` | Profile, session, and resume state |
| `tracker_stack.py` | Stackable vision trackers |
| `trigger_chains.py` | Deterministic event-condition-action chains |
| `unified_approval_runtime.py` | Single approval queue across all subsystems |
| `unified_execution_surface_runtime.py` | Single view across all execution subsystems |
| `unified_workstation_runtime.py` | Unified Workstation (C18.0) |
| `vision_presets.py` | Full CRUD for camera presets |
| `vision_privacy.py` | Hard-coded rules for camera usage |
| `vision_query.py` | Grounded visual question answering |
| `vision_scene.py` | Grounded workspace state from camera frames |
| `visual_context_runtime.py` | Visual Context (C21.2) |
| `visual_operations_runtime.py` | Visual Operations (C21.4) |
| `voice_ingress_runtime.py` | Voice Ingress (C20.0) |
| `voice_operations_runtime.py` | Voice Operations (C20.4) |
| `voice_output_runtime.py` | Voice Output (C20.3) |
| `voice_route_resolver.py` | Separates execution target from audio output device |
| `voice_session_manager.py` | Voice Session Manager (C20.1) |
| `vps_control_catalog.py` | Governed command execution on VPS |
| `work_lane.py` | Multi-session lane routing and foreground guard |
| `workstation_presence_runtime.py` | Operator footprint across the workstation |

### substrate/state/ — State Management (63 files)

`transformation_state_ledger.py` plus 17 subdirectories: `stores/` (15), `memory/` (8), `business/` (3), `config/` (3), `finance/` (3), `metrics/` (3), `registries/` (4), `context/` (2), `lifecycle/` (2), `logs/` (2), `permissions/` (2), `preferences/` (2), `profiles/` (2), `providers/` (2), `session/` (2), `storage/` (2), `tenancy/` (2), `work/` (2).

### substrate/understanding/ — Pattern Recognition & Knowledge (54 files)

`breadth_expansion.py` plus 14 subdirectories: `perception/` (10), `knowledge/` (6), `intelligence/` (6), `domains/` (6), `embedding/` (3), `ontology/` (3), `patterns/` (3), `reality/` (3), `deliberation/` (2), `interpretation/` (2), `research/` (2), `signals/` (2), `world_model/` (2), `world_pulse/` (2).

### substrate/composition/ — Signal Composition & Mastery (45 files)

`knowledge_gap_trigger.py` plus `mastery/` (41 TME primitives and templates), `registries/` (2).

### substrate/sockets/ — Abstract Ports (25 files)

| File | Purpose |
|------|---------|
| `channel_port.py` | Channel routing abstraction |
| `config_port.py` | Configuration port |
| `intelligence_port.py` | Model routing and LLM access |
| `browser_port.py` | Web access adapters |
| `data_source_port.py` | External data adapters |
| `message_port.py` | Messaging abstraction |
| `notification.py` | Notification types |
| `notification_engine.py` | Multi-channel notifications |
| `organism_port.py` | Daemon/organism access |
| `projection_port.py` | Projection consumption layer |
| `capability_socket.py` | Bidirectional execution for integrations |
| `signal_socket.py` | Inbound intake for external integrations |
| `outcome_socket.py` | Outbound result notifications |
| `view_socket.py` | Broadcast pipeline state frames |
| `sensing_port.py` | Perception registration |
| `remote_exec_port.py` | SSH and remote ops |
| `tool_adapter_port.py` | Shell/filesystem/git tools |
| `envelopes.py` | Data shapes that cross the socket boundary |
| `protocols.py` | Protocol definitions for integration contracts |
| `registry.py` | Central registration and generic adapter bridge |

### Other substrate subdirectories

| Directory | Files | Key Files |
|-----------|-------|-----------|
| `operator/` | 19 | `intent_router.py`, `operator_context_engine.py`, `voice_query_engine.py`, `screen_awareness.py` |
| `governance/` | 19 | `authority.py`, `policy_engine.py`, `risk_classes.py`, `security.py` + subdirs: accountability/ (2), policy/ (5), principles/ (2), quality/ (2), validation/ (3) |
| `meta_ide/` | 18 | `engineering_planner.py`, `workspace_observation.py`, `browser_evidence_collector.py` |
| `contracts/` | 12 | `agent_types.py`, `execution_protocol.py`, `governance_protocol.py`, `organism_protocol.py` |
| `reality_model/` | 8 | `canonical.py`, `instance.py`, `reality_intelligence.py`, `simulation.py` |
| `ontology/` | 8 | `laws.py`, `primitives.py`, `relationships.py` + `domains/` (4) |
| `memory/` | 7 | `auto_reconciler.py`, `candidate_generator.py`, `canonical_write.py`, `claude_bridge.py`, `promoter.py`, `watcher.py` |
| `observability/` | 5 | `error_recorder.py`, `jsonl_rotation.py`, `outcome_classifier.py`, `trace_store.py` |
| `integrations/` | 5 | `bridge.py`, `cors.py`, `health.py`, `product_connections.py` |
| `intelligence/` | 4 | `finetune_harness.py`, `runtime.py`, `training_extractor.py` |
| `foundation/` | 4 | `identity.py`, `laws.py`, `perspective.py` |

---

## B2. adapters/ — External System Integrations (100 Python files)

### adapters/models/ — Intelligence Routing (11 files)

| File | Purpose |
|------|---------|
| `model_router.py` | THE entry point for ALL LLM calls. `call_with_fallback()`. Chain: cc_sdk, Gemini, Groq, Ollama |
| `cc_sdk.py` | Claude Code SDK wrapper — reads OAuth token from ancestor process via /proc |
| `llm_adapter.py` | Wraps model_router as a substrate Adapter |
| `agent_runtime.py` | Agent runtime with own fallback via `_claude_available` flag |
| `codex_cli.py` | OpenAI Codex CLI adapter |
| `hermes_cli.py` | Hermes CLI adapter (model-agnostic agent on Beast) |
| `opencode_cli.py` | OpenCode CLI adapter |
| `routing/capabilities.py` | Symbolic capability classes for routing |
| `routing/config.py` | Maps capability classes to runtime kwargs |

### adapters/adapter_engine/ (17 files)

`adapter_manifest.py`, `adapter_maturity.py`, `adapter_lifecycle_manager_v1.py`, `adapter_registry_contracts.py`, `capability_catalog.py`, `capability_discovery.py`, `cu_api_parity_v1.py`, `google_docs_adapter_v1.py`, `google_drive_adapter_v1.py`, `gws_scanner_bridge_v1.py`, `live_drive_docs_ingestion_pipeline_v1.py`, `modality.py`, `participant.py`, `production_manifests.py`, `substrate_candidate_gen_v1.py`, `substrate_decomposer_v1.py`.

### adapters/broadcast/ (9 files)

| File | Purpose |
|------|---------|
| `engine.py` | Broadcast engine — owns FFmpeg subprocess lifecycle |
| `ffmpeg_args.py` | Config to FFmpeg CLI argument list |
| `filtergraph.py` | Scene config to FFmpeg -filter_complex args |
| `process_lifecycle.py` | Subsystem-agnostic subprocess lifecycle manager |
| `scene_model.py` | Scene + SourceEntry models for compositing |
| `zmq_client.py` | ZMQ command client for live FFmpeg parameter control |
| `integration/handlers.py` | Broadcast capability handler |
| `integration/manifest.py` | Broadcast integration manifest |

### adapters/browser_exports/ (8 files)

`chatgpt_export.py`, `claude_export.py`, `instagram_export.py`, `instagram_export_parser.py`, `gmail_export_poller.py`, `contract.py`, `profile_manager.py`.

### adapters/notion/ (13 files)

`notion_publisher.py`, `notion_sync.py`, plus `integration/` (auth, correlation, handlers, manifest, outcomes, poller, signals, transforms, watermarks).

### Other adapter directories

| Directory | Files | Key Files |
|-----------|-------|-----------|
| `browser_auth/` | 3 | `clerk_auth.py`, `sso_chain.py` |
| `browser/` | 3 | Browser automation utilities |
| `calendar/` | 3 | Meeting scheduling, travel management |
| `data_source_adapters/` | 7 | Conversation, GitHub, GWS, local file sources + parsers |
| `github/` | 2 | GitHub Operations via `gh` CLI |
| `google_workspace/` | 7 | `doc_creator.py`, `gws_scanner.py`, `email_gps.py`, `tasks_adapter.py` |
| `scrapling/` | 2 | Web scraping connector |
| `ssh/` | 2 | Centralized SSH/SCP utility |
| `tailscale/` | 2 | Tailscale Admin API adapter |
| `tool_adapters/` | 6 | `base.py`, `filesystem.py`, `git.py`, `shell.py`, `tmux.py` |
| `socket_registration.py` | 1 | Wires concrete adapters into substrate ports |
| `protocol.py` | 1 | Adapter protocol definitions |

---

## B3. transports/ — I/O Surfaces (206 Python files)

### transports/api/ — HTTP API Layer (153 files)

| File | Purpose |
|------|---------|
| `app.py` | FastAPI server entry point |
| `operator.py` | Operator Workstation API |
| `runtime.py` | Control plane runtime — top-level orchestrator wiring |
| `organism_bridge.py` | 155 edges, #1 most-connected. Organism API bridge |
| `cockpit.py` | 111 edges, #2. Core cockpit API endpoints |
| `cockpit_rooms_routes.py` | 110 edges, #3. Conference rooms |
| `cockpit_operator_loop_ext_routes.py` | 56 edges. Operator loop extensions |
| `cockpit_organism_routes.py` | 47 edges. Organism core routes |
| `cockpit_operator_loop_session_routes.py` | 46 edges. Operator loop sessions |
| `cockpit_operator_loop_routes.py` | 46 edges. Operator loop routes |
| `cockpit_spine_router.py` | 43 edges. GovernedExecutionSpine + Journal + MutationRegistry |
| `cockpit_auth.py` | Clerk JWT validation |
| `cockpit_audit.py` | Settings + unified mutation audit trail |
| `governed.py` | `governed_mutation()` wrapper for FastAPI route handlers |
| `signal_factory.py` | Converts HTTP requests to SignalEnvelopes |
| `signal_router.py` | Enforces legal processing pathway for all signals |
| `event_bus.py` | Pub/sub backbone for internal communication |
| `invariants.py` | Validates substrate laws at every transition point |
| `computer_use.py` | Governed multi-layer agent execution |
| `distribution.py` | Channel status, intake, approval, first-boot |
| `voice.py` | Voice session API |
| `workstation.py` | Workstation mode execution, state, health |
| `_mesh_dispatch.py` | Sends engineering tasks to connected nodes via mesh relay |

**Cockpit route files (100+):** Every `cockpit_*_routes.py` maps to a cockpit panel or subsystem. Examples: `cockpit_activity_routes.py` (activity/timeline), `cockpit_agent_fleet_routes.py` (agent coordination), `cockpit_broadcast_routes.py` (broadcast), `cockpit_capability_routes.py` (capability tracking), `cockpit_chat_routes.py` (advisor/DEX conversation), `cockpit_delegation_routes.py` (delegation), `cockpit_engineering_routes.py` (autonomous planning), `cockpit_governance_routes.py` (governance), `cockpit_goal_routes.py` (goals), `cockpit_learning_routes.py` (learning), `cockpit_memory_routes.py` (decision intelligence), `cockpit_organism_map_routes.py` (topology), `cockpit_prediction_routes.py` (predictions), `cockpit_production_routes.py` (software production), `cockpit_push_routes.py` (VAPID key exchange), `cockpit_reality_graph_routes.py` (reality graph), `cockpit_settings_mutations.py` (settings mutations), `cockpit_voice_routes.py` (voice queries), `cockpit_workspace_routes.py` (file browser, diff, test results), and ~60 more.

### transports/discord/ (6 files)

| File | Purpose |
|------|---------|
| `signal_factory.py` | Converts Discord messages to SignalEnvelopes |
| `approval_bridge.py` | Interactive buttons for governance approvals |
| `discord_utils.py` | Discord utility functions |
| `interface_adapter_v1.py` | Discord interface adapter |
| `spine_integration_v1.py` | Discord spine integration |

### transports/node_mesh/ (12 files)

| File | Purpose |
|------|---------|
| `server.py` | NodeMeshServer — WebSocket server (39 edges, top-25) |
| `config.py` | Configuration and token management |
| `registry.py` | Tracks connected mesh nodes and state |
| `metrics_buffer.py` | Per-node ring buffer for telemetry |
| `run.py` | Standalone mesh server launcher |
| `integration/handlers.py` | Proxies execution requests to remote nodes |
| `integration/manifest.py` | Integration manifest for connected nodes |
| `integration/outcomes.py` | Delivers outcomes to remote nodes |
| `integration/signals.py` | Signal types a remote node can emit |
| `integration/types.py` | Pure data types for the mesh |

### transports/channels/ (2 files)

`channel.py` — Channel base class + Discord/Telegram/Webhook/Console implementations.

### transports/presence/ (18 files)

Handlers: `substrate_command_handler.py`, `intent_handler.py`, `cc_command_handler.py`, `pipeline_handler.py`, `voice_handler.py`. Reports (13 files): `adapter_report.py`, `capability_report.py`, `constitution_report.py`, `continuity_report.py`, `economics_report.py`, `epistemic_report.py`, `federation_report.py`, `governance_intelligence_report.py`, `identity_report.py`, `orchestration_report.py`, `resilience_report.py`, `strategy_report.py`, `telos_report.py`.

---

## B4. projections/ — Application-Specific Logic (59 Python files)

### projections/eos/ — EntrepreneurOS (42 files)

#### agents/ (11 files)

| File | Purpose |
|------|---------|
| `base.py` | Base agent with skill execution, permission tiers, governance integration |
| `ceo.py` | CEO Agent — strategic decisions. Permission tier: COMMIT |
| `sales.py` | Sales Agent — pipeline, outreach. Permission tier: EXECUTE |
| `marketing.py` | Marketing Agent — content, brand. Permission tier: EXECUTE |
| `engineering.py` | Engineering Agent — deploy, CI/CD. Permission tier: EXECUTE |
| `finance.py` | Finance Agent — revenue, expense. Permission tier: COMMIT |
| `customer_success.py` | CS Agent — retention, support. Permission tier: EXECUTE |
| `hr.py` | HR Agent — hiring, onboarding. Permission tier: EXECUTE |
| `legal.py` | Legal Agent — contracts, compliance. Permission tier: COMMIT |
| `operations.py` | Ops Agent — workflow automation. Permission tier: EXECUTE |
| `product.py` | Product Agent — roadmap, features. Permission tier: DRAFT |

#### views/ (3 files)

`activity.py` (activity feed), `kpis.py` (business KPI cards), `pipeline.py` (CRM/sales pipeline view).

#### workflows/ (16 files)

| File | Purpose |
|------|---------|
| `runner.py` | WorkflowRunner — executes multi-step workflows through governed mutation |
| `types.py` | Shared workflow data structures |
| `outreach.py` | Prospect outreach sequence |
| `followup.py` | Automated follow-up on stale conversations |
| `content.py` | Content calendar — schedule and track content |
| `research.py` | Governed research with outcome tracking |
| `planning.py` | Governed strategic planning |
| `review.py` | Governed code/work review |
| `execution.py` | Governed task lifecycle tracking |
| `daily.py` | Daily rhythm — morning brief and end-of-day |
| `github.py` | Governed PR and branch operations |
| `browser.py` | Governed web scraping and research |
| `document.py` | Governed document creation |
| `slack.py` | Governed messaging with outbox delivery |
| `design.py` | Governed design asset management |

#### integration/ (8 files)

`manifest.py`, `handlers.py`, `poller.py`, `signals.py`, `outcomes.py`, `tables.py`, `correlation.py`.

### projections/creatoros/ and projections/lyfeos/

Each has the same `integration/` structure as EOS (7 files each).

---

## B5. services/ — Deployment Entrypoints (23 Python files)

| File | Purpose |
|------|---------|
| `discord_bot.py` | Primary Discord bot (os-discord container) |
| `discord_bot_commands.py` | Discord bot command handlers |
| `discord_message_handlers.py` | Discord message processing |
| `operator_api.py` | FastAPI HTTP API (os-operator container) |
| `browser_relay.py` | Playwright browser automation (os-browser container) |
| `overnight_scrape.py` | Batch scraping (os-scraper container) |
| `browser_adapter.py` | Camoufox browser wrapper for anti-detect automation |
| `heartbeat.py` | Service heartbeat monitor |
| `cost_tracker.py` | LLM cost tracking |
| `bridge_health.py` | VPS-side watchdog for the Windows bridge |
| `cc_webhook_receiver.py` | Claude Code webhook receiver |
| `export_bridge_handler.py` | Windows-side handler for fire_export bridge messages |
| `goal_api.py` | Goal management API |
| `higgsfield_webhook.py` | Higgsfield Cloud API webhook receiver |
| `icp_scorer.py` | Ideal Customer Profile scoring |
| `kpi_tracker.py` | KPI tracking |
| `local_bridge_client.py` | Local bridge client |
| `local_bridge_server.py` | Local bridge server |
| `magic_link_handler.py` | Bridge endpoint for intercepting auth emails |
| `magic_link_server.py` | Standalone VPS server for magic-link interception |
| `oauth_device_flow.py` | Headless OAuth re-auth via Tailscale callback |
| `tier_3_fallback.py` | Stub for future UI-TARS / computer-use integration |
| `trigger_export.py` | VPS-side trigger for browser exports on Windows |

---

## B6. cockpit/ — Electron + React Frontend (313 source files)

Deploy with `bash cockpit/deploy.sh`. Never `flyctl deploy` directly.

### cockpit/src/renderer/api/ (10 files)

| File | Purpose |
|------|---------|
| `client.ts` | API client — HTTP requests to the backend |
| `vision-ws.ts` | VisionWsClient (92 edges, top-5) — WebSocket for camera/vision |
| `voice-ws.ts` | Voice WebSocket client |
| `voice-controller.ts` | Voice session controller |
| `voice-turn-assembler.ts` | Assembles voice turns from audio |
| `tts-playback-controller.ts` | Text-to-speech playback |
| `broadcast-ws.ts` | Broadcast WebSocket client |
| `browser-ws.ts` | Browser WebSocket client |
| `device-presence.ts` | Device presence tracker |
| `websocket.ts` | Base WebSocket utilities |

### cockpit/src/renderer/components/ (~90 files)

Core UI shell: `Shell.tsx`, `ControlPanel.tsx`, `LeftRail.tsx`, `RightRail.tsx`, `NavRail.tsx`, `LeftDrawer.tsx`, `RightDrawer.tsx`, `DetailDrawer.tsx`, `TitleBar.tsx`, `HudBar.tsx`, `CommandPalette.tsx`, `GraphView.tsx`, `TopologyMap.tsx`, `TimelineView.tsx`, `VoiceWaveform.tsx`, `CameraPreview.tsx`, `CameraController.tsx`, `VisionPopout.tsx`.

Subdirectories: `canvas/` (20 files — node-based canvases), `cards/` (6 files), `rooms/` (16 files — conference room system), `vision/` (14 files — camera modes, tracking overlays).

### cockpit/src/renderer/panels/ (~70 files)

One panel per subsystem: `ActionsPanel.tsx`, `ActivityPanel.tsx`, `AnalyticsPanel.tsx`, `ApprovalsPanel.tsx`, `BroadcastPanel.tsx`, `BrowserPanel.tsx`, `BuildLoopPanel.tsx`, `CapabilitiesPanel.tsx`, `CommandCenterPanel.tsx`, `ContinuityPanel.tsx`, `DashboardPanel.tsx`, `DelegationPanel.tsx`, `EngineeringPanel.tsx`, `ExecutionPanel.tsx`, `GovernancePanel.tsx`, `InfrastructurePanel.tsx`, `IntelligencePanel.tsx`, `KnowledgePanel.tsx`, `LearningPanel.tsx`, `MemoryPanel.tsx`, `MetaIDEPanel.tsx`, `OperatorHomePanel.tsx`, `OrganismPanel.tsx`, `PresencePanel.tsx`, `ProfilePanel.tsx`, `RealityGraphPanel.tsx`, `SettingsPanel.tsx`, `VisionPanel.tsx`, `WorkPanel.tsx`, and ~40 more.

### cockpit/src/renderer/stores/ (~70 files)

Zustand state stores: `cockpitStore.ts`, `agentStore.ts`, `capabilityMapStore.ts`, `chatStore.ts`, `deviceStore.ts`, `engineeringStore.ts`, `governanceStore.ts`, `intelligenceStore.ts`, `memoryStore.ts`, `organismStore.ts`, `presenceStore.ts`, `settingsStore.ts`, `visionStore.ts`, `voiceStore.ts`, `workflowCanvasStore.ts`, and ~55 more.

### cockpit/src/renderer/hooks/ (12 files)

`useBroadcastConnection.ts`, `useBrowserStream.ts`, `useCanvasDrag.ts`, `useConferenceRoom.ts`, `useIsMobile.ts`, `useKeyboard.ts`, `useOrganismRealtime.ts`, `usePolling.ts`, `useVisionConnection.ts`, `useVoiceDetection.ts`, `useVoiceRoom.ts`.

### cockpit/ other

`src/renderer/App.tsx` (root component), `src/renderer/main.tsx` (entry point), `src/renderer/sw.ts` (service worker), `src/renderer/constants/devices.ts` (device display names), `src/main/index.ts` (Electron main), `src/preload/index.ts` (Electron preload), `deploy.sh`, `package.json`, `vite.config.ts`, `tsconfig.json`, `tailwind.config.js`.

---

## B7. nodes/ — Node Management (51 Python files)

### nodes/distribution/ (3 files)

`distributor.py` (bridges channels to execution pipeline), `first_boot.py` (detects whether system needs onboarding).

### nodes/environments/ (20 files)

`work_packet.py` (WorkPacketRiskLevel, WorkPacketStatus), `vps_local_bridge.py`, `tmux_surface.py`, `bootstrap_plan.py`, `bootstrap_status.py`, `chrome_visible_launch.py`, `execution_binding_contracts.py`, `execution_binding_validator.py`, `heartbeat.py`, `local_pull_protocol.py`, `packet_validator.py`, `queue_paths.py`, `result_ingestion.py`, `w0_packet_builder.py`, `windows_desktop_adapter_contracts.py`, `windows_desktop_adapter_validator.py`, `windows_desktop_request_builder.py`, `workspace_probe.py`.

### nodes/windows/ — Windows Node (28 files)

`kokoro_server.py` (Kokoro TTS Server on Beast GPU), `umh_desktop/tray.py` (system tray companion).

#### umh_node/ (10 files)

`client.py` (WebSocket client), `config.py` (node config), `governance.py` (node-side governance), `launcher.py` (Session 1 launcher), `metrics.py` (system metrics), `peripheral_scanner.py` (WMI peripherals), `service.py` (Windows Service), `subprocess_utils.py` (CREATE_NO_WINDOW flags), `workspace.py` (active window tracking).

#### umh_node/adapters/ (14 files)

`broadcast.py`, `camera.py` (40 edges, top-25), `clipboard.py`, `container.py`, `desktop.py`, `desktop_stream.py`, `filesystem.py`, `hermes.py`, `iou_tracker.py`, `object_detector.py`, `shell.py`, `terminal.py`, `vision_runtime.py`.

---

## B8. umh/ — Relay Servers (3 Python files)

`desktop_relay.py`, `vision_relay.py`, `voice_server.py`.

---

## B9. scripts/ — Utility Scripts (147 files)

### Pre-commit hooks

`check_cpu_gate.py`, `check_dependency_direction.py`, `check_type_divergence.py`, `check_projection_leak.py`, `check_instance_leak.py`, `check_credential_injection.py`, `check_secret_patterns.py`, `check_ungoverned_mutations.py`.

### Graph and knowledge system

`query_graph.py`, `codebase_graph.py`, `incremental_graph.py`, `watch_graph.py`, `merge_graphs.py`, `summarize_nodes.py`, `run_graphify.py`, `build_palace.py`, `build_skill_graph.py`, `session_bootstrap.py`, `verify_knowledge_system.py`, `update-graph`.

### Deploy and infrastructure

`refresh_fly_token.py`, `verify_deploy.py`, `device_sync.py`, `cpu-watchdog.sh`, `install-cpu-watchdog.sh`, `healthcheck.sh`, `run_prod.sh`, `rotate_jsonl.py`, `rotate_secrets.sh`, `backup.sh`, `install_hooks.sh`.

### Scheduled tasks

`scheduled/morning_prep.sh` (5:30am), `scheduled/nightly_consolidation.sh`, `scheduled/nightly_maintenance.sh` (2:00am), `scheduled/weekly_review.sh` (Sunday 6:00am).

### Auth monitoring (scripts/auth_monitor/)

`cc_keepalive.sh`, `credential_coordinator.sh`, `credential_watcher.sh`, `health_check.sh`, `session_resurrector.sh`, `setup_isolation.sh`, `start_session.sh`.

### Memory and ingestion

`memory_continuous_sync.py`, `memory_instant_sync.py`, `memory_watcher_daemon.py`, `ingest_conversations.py`, `ingest_github_repos.py`, `export_pipeline.py`, `fire_export.py`, `github_trinity_ingest.py`.

---

## B10. tests/ — Test Suite (377 Python files)

### tests/substrate/ (3 files)

`test_entity_store.py`, `test_feedback_loop.py`, `test_types.py`.

### tests/adapters/broadcast/ (3 files)

`test_filtergraph.py`, `test_node_dispatch.py`, `test_process_lifecycle.py`.

### tests/certification/ (5 files)

`c28_certification.py`, `c28_panel_audit.py`, `c28_task_acceptance.py`, `c29_benchmark.py` (41 edges), `c29_evidence.py`.

### Campaign tests (130+ files)

`test_c16_integration.py` through `test_c40b_embodiment.py` — each validates a specific campaign.

### Phase tests (80+ files)

`test_phase9_5_spine_native_propagation.py` through `test_phase35_voice_runtime.py` — each tests a specific phase.

### Other tests

P1-P3 convergence tests (20 files), gate tests (6 files), sprint tests (5 files), plus `test_spine_full.py`, `test_governance_full.py`, `test_convergence_acceptance.py`, `test_daemon_e2e.py`, `test_discord_hot_path_smoke.py`, `test_p0_smoke.py`, `test_self_model.py`, `test_reality_ambush.py`, `conftest.py`.

---

## B11. skills/ — Capability Skills (12 directories)

Business: `Content/` (2), `CustomerSuccess/` (2), `Marketing/` (4), `Ops/` (13), `Outreach/` (2), `Research/` (6), `Sales/` (20).

Developer: `developer/` (1), `meta/` (15), `tools/` (254), `saas-dev-skill/` (5170).

---

## B12. knowledge/ — Wiki System

`index.md`, `WIKI_RULES.md`, `retrieval_rules.md`, `cloud_palace.md`, plus subdirectories: `palace/`, `concepts/`, `decisions/`, `domains/`, `entities/`, `skills/`, `sources/`, `synthesis/`.

---

## B13. infra/ — Infrastructure Config

`device_registry.json` (source of truth for devices), `service_dependency_registry.json`, `workspace_registry.json`, `project_registry.json`, `umh_node_registry.json`, `state_authority_registry.json`, `crontab.managed`, `livekit.yaml`, plus `docker/` and `scripts/` subdirectories.

---

## B14. Root-Level Files

Architecture: `ARCHITECTURE.md` (26KB), `PLATFORM_SPEC.md` (29KB, frozen), `PHILOSOPHY.md` (12KB), `EPISTEMOLOGY.md` (21KB), `PROTOCOLS.md` (10KB), `AGENTS.md`, `cloud.md`.

Build: `Dockerfile`, `docker-compose.yml`, `Makefile`, `pyproject.toml`, `requirements.txt`.

Setup: `install.sh`, `setup.sh`, `patch_pycord.py`.

Dotfiles: `.gitignore`, `.dockerignore`, `.env.example`, `.env.sessions.tpl`, `.mcp.json`.

---

## B15. Dot-Directories

| Directory | Purpose |
|-----------|---------|
| `.claude/` | Claude Code config — `CLAUDE.md`, `agents/` (4), `commands/` (24), `hooks/`, `rules/` (10), `skills/` (31) |
| `.agents/` | Installed agent skill packs (17 skills) |
| `.planning/` | GSD workflow state — `PROJECT.md`, `ROADMAP.md`, `STATE.md`, `phases/` (13 dirs) |
| `.obsidian/` | Obsidian vault config |
| `.vscode/` | VS Code settings |
| `.git/` | Git repository with custom hooks |
| `data/` | Runtime state (gitignored) |
| `logs/` | Runtime logs (gitignored) |
| `graphify-out/` | AST index — graph.json (42MB) |

---

## Glossary

| Term | Meaning |
|------|---------|
| **UMH** | Universal Mastery Hierarchy — the platform |
| **Substrate** | The universal platform core (substrate/) |
| **Projection** | An application built on the substrate (EOS, CreatorOS, LyfeOS) |
| **EOS** | EntrepreneurOS — the primary projection |
| **SignalEnvelope** | Canonical input format for all signals entering the substrate |
| **ExecutionSpine** | 8-stage pipeline that processes every signal |
| **Governed Mutation** | Controlled path every state change must follow |
| **WorkPacket** | A unit of work routed through the organism |
| **Organism** | The autonomous agent society running on the substrate |
| **OrganismDaemon** | Daemon managing agent lifecycle |
| **OrchestratorKernel** | Central intelligence routing hub |
| **GovernedExecutionSpine** | THE single mutation gateway |
| **DEX** | The conversational advisor interface |
| **Cockpit** | Electron + React operator control surface |
| **Beast** | Windows workstation with GPU (executor node) |
| **VPS** | Hostinger server (orchestrator node) |
| **Node Mesh** | WebSocket mesh connecting devices via Tailscale |
| **cc_sdk** | Claude Code SDK — LLM calls via subscription |
| **TME** | Tool Mastery Engine — skill system for external tools |
| **BIS** | Business Information System — runtime instance config |
| **ORL** | Operational Readiness Level |
