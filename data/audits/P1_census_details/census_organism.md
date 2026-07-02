# P1 Phase 1A — Capability Census: substrate/organism/

**Date**: 2026-07-01
**Total files**: 282 (excluding __pycache__, tests/, _dormant/)
**Daemon direct imports**: 55 modules
**Daemon transitive reach**: ~120 modules (estimated via import graph)

---

## Classification Key

**Capability**: perception | understanding | reasoning | planning | execution | memory | learning | recovery | world-model | self-model | prediction | reflection | governance | coordination | infrastructure

**Status**:
- **PRODUCTION_ACTIVE** — imported by daemon.py directly
- **TRANSITIVE_ACTIVE** — reachable through daemon's transitive imports
- **PARTIALLY_INTEGRATED** — imported by active modules but not proven exercised
- **DORMANT** — unreachable from production entry points
- **OBSOLETE** — superseded (backward-compat shim or dead campaign code)

---

## Core Runtime (PRODUCTION_ACTIVE — Daemon Direct Imports)

| File | Capability | Status | Importers | Unique Contribution | Canonical? |
|------|-----------|--------|-----------|---------------------|-----------|
| daemon.py | coordination | PRODUCTION_ACTIVE | 14 | Central organism bootstrap and lifecycle — wires all subsystems | YES — the organism entry point |
| governed_spine.py | governance | PRODUCTION_ACTIVE | 9 | THE single mutation gateway — governance→execute→verify→learn→journal→event | YES — canonical mutation path |
| event_spine.py | infrastructure | PRODUCTION_ACTIVE | 65 | Canonical organism-level pub/sub event transport | YES — highest-imported module |
| execution_journal.py | reflection | PRODUCTION_ACTIVE | 13 | Append-only execution ledger for all organism mutations | YES — canonical execution record |
| execution_modes.py | governance | PRODUCTION_ACTIVE | 21 | Governed transition from observation→action (OBSERVE/ASSIST/ACT modes) | YES — mode state machine |
| execution_economy.py | execution | PRODUCTION_ACTIVE | 6 | Runtime cost/value tracking and leverage scoring per execution | YES — cost accounting |
| mutation_registry.py | governance | PRODUCTION_ACTIVE | 10 | Canonical registry of 46 executable mutation types (MutationSpec) | YES — mutation type definitions |
| outcome_learning.py | learning | PRODUCTION_ACTIVE | 17 | Learn from execution outcomes — reliability tracking, fast-path eligibility | YES — canonical learning loop |
| homeostasis.py | recovery | PRODUCTION_ACTIVE | 7 | 9-dimension health monitoring — mode escalation (HEALTHY→CRITICAL) | YES — canonical self-regulation |
| continuous_qualification.py | learning | PRODUCTION_ACTIVE | 1 | Live ORL measurement as daemon tick stage (spot 5min, full hourly) | YES — continuous runtime validation |
| proof_store.py | reflection | PRODUCTION_ACTIVE | 5 | JSONL persistence for proof packages per mutation | YES — canonical proof persistence |
| memory_promotion.py | memory | PRODUCTION_ACTIVE | 9 | Governed promotion from instance→canonical memory with categories | YES — organism memory pipeline |
| template_registry.py | learning | PRODUCTION_ACTIVE | 15 | Reusable executable structures from governed execution history | YES — template persistence |
| store.py | infrastructure | PRODUCTION_ACTIVE | 15 | JSONL persistence for deliverables, messages, agent state | YES — canonical JSONL store |
| advisor.py | coordination | PRODUCTION_ACTIVE | 6 | Top-level orchestrator — routes intent, manages agent work | YES — canonical advisor |
| coordinator.py | coordination | PRODUCTION_ACTIVE | 10 | Hierarchical task decomposition and runtime assignment | YES — task decomposition |
| async_coordinator.py | coordination | PRODUCTION_ACTIVE | 2 | Event-driven objective lifecycle management | YES — async objective tracking |
| allocation_loop.py | coordination | PRODUCTION_ACTIVE | 2 | Continuous leverage-based runtime allocation cycle | YES — resource allocation |
| autonomous_tick.py | infrastructure | PRODUCTION_ACTIVE | 2 | Continuous organism metabolism heartbeat — runs all tick stages | YES — canonical tick engine |
| autonomous_cadence.py | governance | PRODUCTION_ACTIVE | 4 | Scheduled autonomous improvement discovery with cadence policy | YES — autonomous timing |
| autonomous_action_gateway.py | governance | PRODUCTION_ACTIVE | 5 | Structural enforcement of spine-routed mutation for autonomous actions | YES — autonomous governance |
| automation_pipeline.py | execution | PRODUCTION_ACTIVE | 2 | Promote repeated operator interventions to automation candidates | YES — automation discovery |
| maintenance_loop.py | recovery | PRODUCTION_ACTIVE | 8 | OBSERVE-mode infrastructure health cycle (repo, docker, disk) | YES — preventive maintenance |
| spine_guard.py | governance | PRODUCTION_ACTIVE | 8 | Enforcement layer for single-spine mutation doctrine | YES — recursion/safety guard |
| recursion_governance.py | governance | PRODUCTION_ACTIVE | 5 | Bounded recursive execution control with depth limits | YES — recursion safety |
| runtime_supervisor.py | recovery | PRODUCTION_ACTIVE | 10 | Persistent runtime lifecycle management — crash detection, restart | YES — runtime health |
| runtime_graph.py | world-model | PRODUCTION_ACTIVE | 25 | Canonical runtime registry with dynamic availability and scoring | YES — runtime topology |
| environment_graph.py | world-model | PRODUCTION_ACTIVE | 2 | Continuously updated operational world-state graph | YES — environment state |
| environment_reconciler.py | recovery | PRODUCTION_ACTIVE | 2 | Continuous drift correction for environment state | YES — environment repair |
| mesh_reconciler.py | world-model | PRODUCTION_ACTIVE | 1 | Syncs RuntimeGraph with live mesh relay | YES — mesh state sync |
| tailscale_discovery.py | perception | PRODUCTION_ACTIVE | 1 | Diffs tailscale peers vs device registry | YES — network discovery |
| bottleneck_engine.py | prediction | PRODUCTION_ACTIVE | 4 | Operational self-optimization — detects performance constraints | YES — bottleneck detection |
| leverage_engine.py | prediction | PRODUCTION_ACTIVE | 2 | Determines highest-impact actions based on evidence | YES — leverage scoring |
| leverage_metrics.py | prediction | PRODUCTION_ACTIVE | 13 | Operational leverage measurement — actual organism value | YES — leverage tracking |
| leverage_assimilation.py | learning | PRODUCTION_ACTIVE | 6 | Ingest, classify, and operationalize external leverage | YES — external knowledge intake |
| objective_physics.py | planning | PRODUCTION_ACTIVE | 3 | Causal execution dynamics — momentum, dependency physics | YES — objective dynamics |
| objective_queue.py | planning | PRODUCTION_ACTIVE | 2 | Intake front door for OrganismCoordinator objectives | YES — objective intake |
| operator_compression.py | execution | PRODUCTION_ACTIVE | 9 | Reduce human operational burden through automation detection | YES — operator load reduction |
| workload_probes.py | perception | PRODUCTION_ACTIVE | 2 | Live operational pressure measurement into the organism | YES — workload sensing |
| workload_runner.py | execution | PRODUCTION_ACTIVE | 8 | Governed execution of operational jobs | YES — job execution |
| worker_cell.py | execution | PRODUCTION_ACTIVE | 5 | Bounded task execution through existing pipeline | YES — task executor |
| workcell_daemon.py | coordination | PRODUCTION_ACTIVE | 2 | Persistent processor for workcell inboxes | YES — workcell inbox loop |
| workcell_protocol.py | coordination | PRODUCTION_ACTIVE | 3 | Durable inbox/outbox execution cells (V2 protocol) | YES — workcell contract |
| agent_capability_model.py | self-model | PRODUCTION_ACTIVE | 11 | Track agent reliability per capability | YES — agent capability tracking |
| assisted_executor.py | execution | PRODUCTION_ACTIVE | 4 | Governed execution of approved maintenance actions | YES — assisted maintenance |
| plan_execution_adapter.py | planning | PRODUCTION_ACTIVE | 8 | Bridges CompositionPlan to GovernedExecutionSpine (DAG→ActionEnvelope) | YES — plan→spine bridge |
| candidate_supply_engine.py | prediction | PRODUCTION_ACTIVE | 5 | Discovers improvement candidates from real organism sources | YES — improvement discovery |
| capability_compounding_runtime.py | learning | PRODUCTION_ACTIVE | 2 | Campaign 22.4 — capability compounding metrics | Partial — overlaps compounding_engine |
| readiness_model.py | self-model | PRODUCTION_ACTIVE | 5 | 6-dimension readiness assessment | YES — readiness scoring |
| dev_session_tracker.py | execution | PRODUCTION_ACTIVE | 1 | Wraps development sessions as governed spine executions | YES — dev session governance |
| projection_port.py | infrastructure | PRODUCTION_ACTIVE | 2 | Projection-agnostic organism state port | YES — state projection |
| approval_store.py | governance | PRODUCTION_ACTIVE | 6 | JSONL persistence for governance-blocked signals | YES — approval persistence |
| propagation_wiring.py | infrastructure | PRODUCTION_ACTIVE | 1 | Registers all propagation targets with the engine | YES — propagation setup |
| next_action_engine.py | planning | PRODUCTION_ACTIVE | 2 | Evidence-based action recommender | YES — next action selection |

---

## Transitively Active (reachable through daemon imports)

| File | Capability | Status | Importers | Unique Contribution | Canonical? |
|------|-----------|--------|-----------|---------------------|-----------|
| action_envelope.py | governance | TRANSITIVE_ACTIVE | 17 | Canonical executable object for ALL organism mutations | YES — mutation envelope |
| action_bridge.py | execution | TRANSITIVE_ACTIVE | 3 | Governed composition of catalog, observation, and execution | YES — action orchestration |
| action_catalog.py | governance | TRANSITIVE_ACTIVE | 3 | Data-driven registry of governed operator actions | YES — action definitions |
| mutation_router.py | governance | TRANSITIVE_ACTIVE | 1 | Canonical choke point for all organism state mutations | YES — mutation routing |
| propagation_graph.py | infrastructure | TRANSITIVE_ACTIVE | 7 | Dependency-aware change propagation model | YES — change propagation |
| propagation_graph_builder.py | infrastructure | TRANSITIVE_ACTIVE | 2 | Extracts nodes and edges from real system state | YES — graph construction |
| propagation_planner.py | planning | TRANSITIVE_ACTIVE | 3 | Creates wave-based propagation plans from change events | YES — propagation planning |
| propagation_executor.py | execution | TRANSITIVE_ACTIVE | 2 | Executes propagation plans in dry-run or governed mode | YES — propagation execution |
| change_event.py | infrastructure | TRANSITIVE_ACTIVE | 6 | State change model for propagation planning | YES — change event type |
| slo_definitions.py | governance | TRANSITIVE_ACTIVE | 1 | 8 concrete SLO targets enforced through homeostasis | YES — SLO definitions |
| protocols.py | infrastructure | TRANSITIVE_ACTIVE | 14 | Typed contracts for the agent society | YES — protocol definitions |
| qualification_harness.py | learning | TRANSITIVE_ACTIVE | 1 | Qualification campaign — proves operational properties under load | YES — qualification engine |
| world_model.py | self-model | TRANSITIVE_ACTIVE | 13 | Organism-level self-model — subsystems, status, evidence, gaps | YES — organism self-knowledge |
| reality_graph.py | world-model | TRANSITIVE_ACTIVE | 13 | Canonical operator-world graph (entities, relationships, evidence) | YES — reality representation |
| presence_runtime.py | perception | TRANSITIVE_ACTIVE | 13 | Operator presence awareness — online/offline/active state | YES — presence tracking |
| dependency_graph.py | infrastructure | TRANSITIVE_ACTIVE | 13 | Subsystem dependency model for UMH | YES — dependency tracking |
| composition_engine.py | planning | TRANSITIVE_ACTIVE | 11 | Deterministic intent→plan from observed capabilities | YES — plan composition |
| intent_classifier.py | understanding | TRANSITIVE_ACTIVE | 7 | Converts raw user intent into structured classification | YES — intent classification |
| work_packet.py | execution | TRANSITIVE_ACTIVE | 11 | Canonical intent-to-execution container | YES — work unit type |
| work_packet_engine.py | execution | TRANSITIVE_ACTIVE | 15 | Creates work packets from user intent | YES — work creation |
| universal_work_queue.py | execution | TRANSITIVE_ACTIVE | 15 | Canonical queue for all work packets | YES — work queue |
| empire_router.py | coordination | TRANSITIVE_ACTIVE | 6 | Routes founder intent to domain-classified, governed WorkPackets | YES — domain routing |
| agent_registry.py | coordination | TRANSITIVE_ACTIVE | 5 | Agent types, capabilities, permissions, and routing | YES — agent registry |
| agents.py | coordination | TRANSITIVE_ACTIVE | 2 | Concrete agent cells — Researcher, Builder, AutoResearch | YES — agent implementations |
| agent_runtime.py | execution | TRANSITIVE_ACTIVE | 3 | Agent base runtime — foundational behavior of every agent | YES — agent base |
| agent_fleet_runtime.py | coordination | TRANSITIVE_ACTIVE | 5 | Unified agent coordination layer | YES — fleet management |
| device_role_registry.py | world-model | TRANSITIVE_ACTIVE | 7 | Tracks device roles and capabilities in the UMH organism | YES — device role tracking |
| umh_node_registry.py | world-model | TRANSITIVE_ACTIVE | 11 | Canonical registry of UMH organism nodes | YES — node registry |
| umh_node_topology.py | world-model | TRANSITIVE_ACTIVE | 3 | Canonical node role and version models | YES — node topology |
| workcell.py | coordination | TRANSITIVE_ACTIVE | 3 | Planning/delegation workcell model for Work Packets | YES — workcell planning |
| handoff.py | coordination | TRANSITIVE_ACTIVE | 2 | Structured agent-to-agent task transfer | YES — agent handoff |
| parallel.py | coordination | TRANSITIVE_ACTIVE | 1 | Parallel agent execution — run multiple agents concurrently | YES — parallel dispatch |
| worker_lifecycle.py | coordination | TRANSITIVE_ACTIVE | 1 | Structured lifecycle events for workers | YES — lifecycle events |
| worker_registry.py | coordination | TRANSITIVE_ACTIVE | 3 | Active worker inventory per device | YES — worker tracking |
| runtime_session.py | execution | TRANSITIVE_ACTIVE | 5 | Governed execution surface for workcell runtimes | YES — session model |
| runtime_manager.py | execution | TRANSITIVE_ACTIVE | 4 | Orchestrates governed runtime session lifecycle | YES — session lifecycle |
| runtime_adapter.py | execution | TRANSITIVE_ACTIVE | 3 | Abstract contract for execution surfaces | YES — adapter interface |
| runtime_adapters.py | execution | TRANSITIVE_ACTIVE | 4 | Concrete RuntimeAdapter implementations | YES — adapter implementations |
| trust_score.py | governance | TRANSITIVE_ACTIVE | 4 | Composite trust scoring via weakest-link gate | YES — trust assessment |
| risk_engine.py | governance | TRANSITIVE_ACTIVE | 1 | Unified risk register synthesis | YES — risk assessment |
| approval_gate.py | governance | TRANSITIVE_ACTIVE | 5 | Requires explicit approval before sandbox execution | YES — approval enforcement |
| worktree_sandbox.py | execution | TRANSITIVE_ACTIVE | 8 | Isolated execution environments for autonomous improvements | YES — sandbox management |
| autonomous_improvement_lane.py | execution | TRANSITIVE_ACTIVE | 4 | Bounded autonomous LOW-risk self-improvement | YES — autonomous improvement |
| autonomous_pr_factory.py | execution | TRANSITIVE_ACTIVE | 4 | Converts eligible improvements into isolated PRs | YES — PR creation |
| changeset_manifest.py | reflection | TRANSITIVE_ACTIVE | 1 | Evidence record for every autonomous branch/PR | YES — changeset tracking |
| template_governance.py | governance | TRANSITIVE_ACTIVE | 4 | 9-dimension scoring engine for template cadence eligibility | YES — template quality |
| template_seeder.py | learning | TRANSITIVE_ACTIVE | 1 | Seeds evidence-backed execution templates to runtime store | YES — template seeding |
| promotion_threshold_policy.py | governance | TRANSITIVE_ACTIVE | 1 | Governs cadence mode transitions (threshold policies) | YES — promotion policy |
| reliability_signals.py | learning | TRANSITIVE_ACTIVE | 3 | Normalizes production-backed signals for cadence ranking | YES — signal normalization |
| reliability_weighted_ranker.py | prediction | TRANSITIVE_ACTIVE | 1 | Deterministic candidate ranking using production signals | YES — candidate ranking |

---

## Partially Integrated (imported by active code but not proven exercised)

| File | Capability | Status | Importers | Unique Contribution | Canonical? |
|------|-----------|--------|-----------|---------------------|-----------|
| advisor_conversation.py | coordination | PARTIALLY_INTEGRATED | 2 | Multi-turn conversation with intent routing | YES — conversational advisor |
| advisor_hierarchy.py | coordination | PARTIALLY_INTEGRATED | 2 | Governed recursive advisory orchestration | Unique — recursive advisory |
| advisor_reconciliation.py | understanding | PARTIALLY_INTEGRATED | 1 | Detects reconciliation intent in operator input | Unique — reconciliation detection |
| council.py | reasoning | PARTIALLY_INTEGRATED | 2 | Multi-perspective advisory (7 roles: strategist, skeptic, etc.) | YES — deliberation council |
| decision_registry.py | reasoning | PARTIALLY_INTEGRATED | 6 | First-class strategic decision records | YES — decision persistence |
| decision_impact_engine.py | reasoning | PARTIALLY_INTEGRATED | 5 | Blast radius analysis for strategic decisions | Unique — impact analysis |
| decision_lineage_engine.py | reasoning | PARTIALLY_INTEGRATED | 2 | Causal chain traversal for decisions | Unique — lineage tracking |
| decision_validity_engine.py | reasoning | PARTIALLY_INTEGRATED | 5 | Evaluates whether decisions still make sense | Unique — validity checking |
| strategic_gap_engine.py | planning | PARTIALLY_INTEGRATED | 14 | Gap analysis: current reality→target goals→gaps→work packets | YES — gap analysis (most-connected planning module) |
| strategic_planning_engine.py | planning | PARTIALLY_INTEGRATED | 7 | Generate plans linking current reality to goals (deterministic) | YES — strategic planning |
| strategic_memory_engine.py | memory | PARTIALLY_INTEGRATED | 4 | Institutional memory with timeline snapshots and replay | Unique — temporal memory |
| strategic_context_runtime.py | reasoning | PARTIALLY_INTEGRATED | 1 | Unified executive synthesis facade over all strategic engines | Designed as canonical facade — but only 1 importer |
| strategic_tick_loop.py | coordination | PARTIALLY_INTEGRATED | 5 | Continuous governed awareness engine | Overlaps daemon tick stages |
| goal_alignment_engine.py | planning | PARTIALLY_INTEGRATED | 6 | Ensure work supports goals — detect orphan work/goals | Unique — alignment checking |
| goal_drift_engine.py | planning | PARTIALLY_INTEGRATED | 3 | Detect movement away from objectives (4 drift types) | Unique — drift detection |
| goal_hierarchy_engine.py | planning | PARTIALLY_INTEGRATED | 2 | Structural operations on the goal tree | Unique — tree traversal |
| institutional_memory_runtime.py | memory | PARTIALLY_INTEGRATED | 3 | Knowledge promotion lifecycle (PROPOSED→CANONICAL→RETIRED) | Unique — knowledge lifecycle |
| learning_extraction_runtime.py | learning | PARTIALLY_INTEGRATED | 8 | Campaign 12.0 — extract learning from execution history | Unique — learning extraction |
| learning_portfolio_runtime.py | learning | PARTIALLY_INTEGRATED | 12 | Campaign 12.3 — portfolio-level learning metrics | Unique — learning portfolio |
| outcome_pattern_engine.py | learning | PARTIALLY_INTEGRATED | 5 | Campaign 12.1 — pattern detection in outcomes | Unique — outcome patterns |
| outcome_tracking_runtime.py | learning | PARTIALLY_INTEGRATED | 6 | Measure progress toward goals via outcomes | Unique — progress tracking |
| outcome_verification.py | learning | PARTIALLY_INTEGRATED | 1 | Replaces 'Task Complete' with 'Outcome Verified' | Unique — verification protocol |
| prediction_portfolio_runtime.py | prediction | PARTIALLY_INTEGRATED | 9 | Campaign 13.2 — prediction tracking and accuracy | Unique — prediction portfolio |
| self_model_predictor.py | self-model | PARTIALLY_INTEGRATED | 1 | Statistical self-prediction engine for the organism | Unique — self-prediction |
| capability_graph_engine.py | self-model | PARTIALLY_INTEGRATED | 1 | Explicit dependency/composition edges between capabilities | Unique — capability graph |
| capability_gap_engine.py | planning | PARTIALLY_INTEGRATED | 6 | Goal-to-capability mapping — detect missing capabilities | Unique — capability gap analysis |
| capability_portfolio_runtime.py | self-model | PARTIALLY_INTEGRATED | 9 | Portfolio health, gap analysis, bottleneck detection | Unique — capability portfolio |
| capability_evolution_engine.py | learning | PARTIALLY_INTEGRATED | 6 | Campaign 12.2 — capability maturity lifecycle | Unique — capability evolution |
| capability_runtime.py | self-model | PARTIALLY_INTEGRATED | 5 | Emergent capability tracking and maturity lifecycle | Unique — capability lifecycle |
| compounding_engine.py | learning | PARTIALLY_INTEGRATED | 6 | Turn internal learning into leverage | Partial overlap with capability_compounding_runtime |
| coherence_propagation.py | infrastructure | PARTIALLY_INTEGRATED | 6 | Parallel dependent-system updates on verified change | Unique — coherence maintenance |
| contradiction_engine.py | reasoning | PARTIALLY_INTEGRATED | 11 | Detect mismatches between declared and observed reality | Unique — contradiction detection |
| drift_detection_engine.py | recovery | PARTIALLY_INTEGRATED | 3 | Unified drift synthesis across dimensions | Unique — drift synthesis |
| governance_runtime.py | governance | PARTIALLY_INTEGRATED | 10 | C15.0 — governance policy evaluation layer | Unique — runtime governance layer |
| governed_execution_runtime.py | governance | PARTIALLY_INTEGRATED | 9 | Campaign 16.0 — governed execution contracts | Overlaps governed_spine |
| governed_work_runtime.py | governance | PARTIALLY_INTEGRATED | 5 | Mandatory execution gateway | Overlaps governed_spine |
| execution_coordinator.py | coordination | PARTIALLY_INTEGRATED | 11 | Canonical orchestration layer (Phase 13) | Overlaps coordinator |
| executor_runtime.py | execution | PARTIALLY_INTEGRATED | 10 | Canonical execution contract layer (Phase 14) | YES — executor contracts |
| work_portfolio_runtime.py | reflection | PARTIALLY_INTEGRATED | 12 | Execution health, velocity, and drift detection | Unique — work portfolio metrics |
| work_graph.py | reflection | PARTIALLY_INTEGRATED | 5 | Read-only query projection over existing work stores | Unique — work graph query |
| work_readiness_runtime.py | planning | PARTIALLY_INTEGRATED | 4 | Multi-dimensional readiness classification for work | Unique — work readiness |
| work_recovery_runtime.py | recovery | PARTIALLY_INTEGRATED | 3 | Maps work states to recovery actions | Unique — work recovery |
| packet_router.py | execution | PARTIALLY_INTEGRATED | 1 | Capability-first work routing | Unique — capability routing |
| delegation_runtime.py | coordination | PARTIALLY_INTEGRATED | 4 | Intent classification, delegation proposals, mission lifecycle | Unique — delegation management |
| delegation_readiness_runtime.py | coordination | PARTIALLY_INTEGRATED | 6 | Pre-assignment feasibility + outcome prediction for delegation | Unique — delegation assessment |
| delegation_topology.py | coordination | PARTIALLY_INTEGRATED | 4 | Chooses execution structure for a work packet | Unique — topology planning |
| delegation_followup.py | coordination | PARTIALLY_INTEGRATED | 1 | Checks overdue delegations and acts | Unique — delegation followup |
| distributed_runtime.py | execution | PARTIALLY_INTEGRATED | 5 | Facade composing all distributed runtime subsystems | Unique — distributed facade |
| session_runtime.py | execution | PARTIALLY_INTEGRATED | 7 | Canonical session architecture for UMH | YES — session management |
| profile_runtime.py | self-model | PARTIALLY_INTEGRATED | 5 | Canonical authority for operator work identity and system modes | YES — operator profile |
| device_awareness.py | perception | PARTIALLY_INTEGRATED | 3 | Deterministic device detection and capability routing | Unique — device detection |
| device_capacity.py | world-model | PARTIALLY_INTEGRATED | 2 | Per-device worker slots and backpressure | Unique — capacity model |
| device_provisioner.py | execution | PARTIALLY_INTEGRATED | 2 | Multi-OS diagnosis + role-based provisioning | Unique — device provisioning |
| device_registry_writer.py | infrastructure | PARTIALLY_INTEGRATED | 4 | Atomic writes + cache invalidation for device registry | Unique — registry writer |
| umh_version_coherence.py | governance | PARTIALLY_INTEGRATED | 2 | Detects version drift across nodes | Unique — version coherence |
| compute_fabric_runtime.py | world-model | PARTIALLY_INTEGRATED | 4 | Unified compute body map | Unique — compute inventory |
| service_dependency_graph.py | infrastructure | PARTIALLY_INTEGRATED | 4 | Canonical service dependency models | Unique — service deps |
| service_dependency_registry.py | infrastructure | PARTIALLY_INTEGRATED | 2 | Canonical registry of service dependencies | Unique — dep registry |
| service_failure_engine.py | recovery | PARTIALLY_INTEGRATED | 5 | Computes failure impact across service graph | Unique — failure impact |
| state_coherence_engine.py | governance | PARTIALLY_INTEGRATED | 5 | Detects state authority coherence across nodes | Unique — state coherence |
| state_authority_graph.py | governance | PARTIALLY_INTEGRATED | 2 | Canonical state domain authority models | Unique — authority graph |
| state_registry.py | infrastructure | PARTIALLY_INTEGRATED | 3 | Canonical registry of state domain authorities | Unique — state domains |
| source_registry.py | infrastructure | PARTIALLY_INTEGRATED | 4 | Tracks all context sources available to UMH | Unique — source inventory |
| projection_engine.py | prediction | PARTIALLY_INTEGRATED | 9 | Predictive world-model layer for UMH | Unique — prediction engine |
| projection_source_registry.py | infrastructure | PARTIALLY_INTEGRATED | 5 | Tracks sources per projection for reconciliation | Unique — projection sources |
| projection_reconciliation_engine.py | recovery | PARTIALLY_INTEGRATED | 3 | Diagnoses divergence across projection sources | Unique — projection reconciliation |
| projection_readiness_gate.py | governance | PARTIALLY_INTEGRATED | 3 | Blocks feature build until source reconciliation is sufficient | Unique — readiness gate |
| projection_certification.py | governance | PARTIALLY_INTEGRATED | 3 | Graduated L0-L5 certification framework | Unique — certification levels |
| projection_integration_runtime.py | infrastructure | PARTIALLY_INTEGRATED | 2 | Audit/mapping layer over projections | Unique — projection audit |
| context_diagnostic.py | understanding | PARTIALLY_INTEGRATED | 4 | Diagnostic reports on context state | Unique — context diagnostics |
| context_ingestion_engine.py | understanding | PARTIALLY_INTEGRATED | 2 | Ingest local/system context sources | Unique — context ingestion |
| context_resolution.py | understanding | PARTIALLY_INTEGRATED | 3 | "The system already knows" layer — resolves implicit context | Unique — context resolution |
| continuity_runtime.py | infrastructure | PARTIALLY_INTEGRATED | 8 | Operational continuity engine for UMH | Unique — continuity assurance |
| canonical_update.py | governance | PARTIALLY_INTEGRATED | 5 | Proposed changes to canonical truth | Unique — canonical change proposals |
| command_runtime.py | execution | PARTIALLY_INTEGRATED | 2 | Canonical intent-to-action layer for all operator surfaces | Unique — command dispatch |
| mission.py | coordination | PARTIALLY_INTEGRATED | 1 | Bridge between user conversation and organism execution | Unique — mission model |
| observability.py | infrastructure | PARTIALLY_INTEGRATED | 4 | Unified dashboard snapshot | Unique — observability snapshot |
| report_dispatcher.py | infrastructure | PARTIALLY_INTEGRATED | 2 | Sends task completion reports to Discord + cockpit chat | YES — report delivery |
| grounded_handlers.py | execution | PARTIALLY_INTEGRATED | 1 | Deterministic answers backed by real data | Unique — grounded responses |
| grounding_registry.py | understanding | PARTIALLY_INTEGRATED | 2 | Source data requirements for deterministic status answers | Unique — grounding requirements |
| diagnostic_engine.py | understanding | PARTIALLY_INTEGRATED | 2 | Analyze ingested context for canonical truth state | Unique — truth analysis |
| impact_analyzer.py | reasoning | PARTIALLY_INTEGRATED | 4 | Computes change impact across the propagation graph | Unique — impact computation |
| domain_registry.py | infrastructure | PARTIALLY_INTEGRATED | 4 | First-class domain definitions for empire routing | Unique — domain registry |
| knowledge_model_registry.py | understanding | PARTIALLY_INTEGRATED | 3 | System knowledge containers | Unique — knowledge models |
| assumption_tracking_runtime.py | reasoning | PARTIALLY_INTEGRATED | 2 | Governed assumption records for UMH | Unique — assumption tracking |
| workspace_awareness.py | perception | PARTIALLY_INTEGRATED | 6 | Deterministic active-context detection | Unique — workspace sensing |
| tradeoff_intelligence_engine.py | reasoning | PARTIALLY_INTEGRATED | 6 | C14.1 — tradeoff analysis for resource allocation | Unique — tradeoff analysis |
| trajectory_intelligence_runtime.py | prediction | PARTIALLY_INTEGRATED | 5 | Campaign 13.0 — trajectory tracking and projection | Unique — trajectory intelligence |
| scenario_intelligence_engine.py | prediction | PARTIALLY_INTEGRATED | 2 | Campaign 13.1 — scenario analysis | Unique — scenario modeling |
| role_contracts.py | coordination | PARTIALLY_INTEGRATED | 3 | Template-based role definitions with capability profiles | Unique — role templates |
| roadmap_engine.py | planning | PARTIALLY_INTEGRATED | 3 | Phase linkage model for self-build queue | Unique — roadmap model |
| self_build_queue.py | planning | PARTIALLY_INTEGRATED | 5 | Canonical work item model and queue engine | Unique — self-build tracking |
| workload_placement_policy.py | coordination | PARTIALLY_INTEGRATED | 4 | Selects correct runtime + device for Work Packets | Unique — placement policy |
| workstation_runtime.py | execution | PARTIALLY_INTEGRATED | 4 | Canonical workstation planning layer (Phase 10) | Unique — workstation planning |
| resource_allocation_runtime.py | coordination | PARTIALLY_INTEGRATED | 5 | C14.0 — resource allocation runtime | Overlaps allocation_loop |
| executive_brief_runtime.py | reflection | PARTIALLY_INTEGRATED | 2 | Structured operator briefing synthesis | Unique — executive briefs |
| executive_portfolio_runtime.py | reflection | PARTIALLY_INTEGRATED | 6 | C14.2 — executive portfolio synthesis | Unique — portfolio synthesis |
| organism_portfolio_runtime.py | reflection | PARTIALLY_INTEGRATED | 6 | C15.3 — organism portfolio metrics | Unique — organism metrics |
| priority_engine.py | planning | PARTIALLY_INTEGRATED | 1 | Deterministic priority synthesis | Unique — priority calculation |
| recommendation_engine.py | planning | PARTIALLY_INTEGRATED | 1 | Unified action recommendation synthesis | Unique — recommendation |
| trial_runner.py | learning | PARTIALLY_INTEGRATED | 4 | Self-improvement reliability trial execution | Unique — trial management |
| reconciliation_engine.py | understanding | PARTIALLY_INTEGRATED | 2 | Structured context reconciliation sessions | Unique — reconciliation |
| reconciliation_session.py | understanding | PARTIALLY_INTEGRATED | 3 | Structured operator-AI context alignment | Unique — alignment sessions |
| cross_source_reconciler.py | understanding | PARTIALLY_INTEGRATED | 1 | Detect relationships across fragmented sources | Unique — cross-source analysis |
| ingestion_job.py | execution | PARTIALLY_INTEGRATED | 4 | Tracks context ingestion work units | Unique — ingestion tracking |
| claude_code_runtime_adapter.py | execution | PARTIALLY_INTEGRATED | 1 | Claude Code PTY runtime adapter skeleton | Unique — CC adapter |
| shell_runtime_adapter.py | execution | PARTIALLY_INTEGRATED | 1 | Safe subprocess execution surface | Unique — shell adapter |
| production_planning_runtime.py | planning | PARTIALLY_INTEGRATED | 1 | C22.1 — converts "Build X" into full lifecycle plan | Unique — production planning |
| production_merge_verifier.py | governance | PARTIALLY_INTEGRATED | 2 | Confirms sandboxed PR became production truth | Unique — merge verification |
| production_truth_delta.py | reflection | PARTIALLY_INTEGRATED | 2 | What actually changed in production after merge | Unique — delta tracking |
| production_ops_runtime.py | execution | PARTIALLY_INTEGRATED | 1 | Campaign 22.0 — production operations | Overlaps workload_runner |
| production_review_runtime.py | governance | PARTIALLY_INTEGRATED | 1 | C22.3 — production review | Unique — review tracking |
| production_workforce_runtime.py | coordination | PARTIALLY_INTEGRATED | 1 | Campaign 22.2 — workforce management | Unique — workforce model |
| product_factory_runtime.py | execution | PARTIALLY_INTEGRATED | 1 | C22.5 — product factory | Unique — product creation |
| meta_ide_runtime.py | execution | PARTIALLY_INTEGRATED | 2 | Unified development surface | Unique — meta IDE |
| development_session_bridge.py | execution | PARTIALLY_INTEGRATED | 1 | Makes coding agents governed organs of the organism | Unique — dev session bridging |
| agent_execution_runner.py | execution | PARTIALLY_INTEGRATED | 1 | Invokes coding agents inside governed sandboxes | Unique — agent sandbox execution |
| operator_acceptance.py | governance | PARTIALLY_INTEGRATED | 3 | End-to-end acceptance test tracking | Unique — acceptance testing |
| operator_acceptance_mode.py | governance | PARTIALLY_INTEGRATED | 2 | Standard vs deterministic-only vs blocked modes | Unique — acceptance modes |
| operator_acceptance_scenarios.py | governance | PARTIALLY_INTEGRATED | 2 | Predefined end-to-end test scenarios | Unique — test scenarios |
| operator_readiness_gate.py | governance | PARTIALLY_INTEGRATED | 4 | Phase 13.4 readiness assessment | Unique — readiness gating |
| operator_session.py | execution | PARTIALLY_INTEGRATED | 3 | Conversational state for operator-orchestrator interaction | Unique — session state |
| operator_response.py | execution | PARTIALLY_INTEGRATED | 2 | Structured response contract for orchestrator kernel | Unique — response contract |
| permission_dialogue.py | governance | PARTIALLY_INTEGRATED | 2 | Socratic permission engine — ask before expanding access | Unique — permission negotiation |
| sync_policy.py | governance | PARTIALLY_INTEGRATED | 1 | External sync policy — governs UMH↔external tool relations | Unique — sync governance |
| system_identity.py | infrastructure | PARTIALLY_INTEGRATED | 2 | Canonical UMH identity — single source of truth | YES — system identity |
| embodiment_runtime.py | execution | PARTIALLY_INTEGRATED | 1 | Natural language intent becomes governed work | Unique — embodiment |
| proof_runtime.py | reflection | PARTIALLY_INTEGRATED | 2 | Complete proof packages per execution | Overlaps proof_store |
| orchestrator_kernel.py | coordination | PARTIALLY_INTEGRATED | 4 | Central intelligence routing for operator interaction | Unique — orchestrator routing |
| orchestrator_awareness_runtime.py | self-model | PARTIALLY_INTEGRATED | 3 | Synthesized reality model for the orchestrator | Unique — orchestrator self-awareness |
| organism_coordination_engine.py | coordination | PARTIALLY_INTEGRATED | 2 | C15.1 — organism coordination | Overlaps coordinator |
| organism_state_runtime.py | infrastructure | PARTIALLY_INTEGRATED | 4 | Campaign 16.1 — organism state management | Unique — state management |
| source_truth_runtime.py | understanding | PARTIALLY_INTEGRATED | 1 | Full organizational lineage (Campaign 22.6 CORE) | Unique — source truth |
| execution_lifecycle_runtime.py | execution | PARTIALLY_INTEGRATED | 2 | Campaign 16.2 — execution lifecycle | Unique — lifecycle tracking |
| execution_graph.py | reflection | PARTIALLY_INTEGRATED | 1 | Evidence-grade lineage validation over execution infra | Unique — execution lineage |
| execution_ledger.py | reflection | PARTIALLY_INTEGRATED | 1 | Canonical record of every execution request and outcome | Overlaps execution_journal |
| capability_validation_runtime.py | learning | PARTIALLY_INTEGRATED | 1 | Benchmark storage, reporting, and freshness tracking | Unique — validation tracking |
| artifact_registry.py | infrastructure | PARTIALLY_INTEGRATED | 1 | Indexes produced outputs across UMH | Unique — artifact inventory |
| project_registry.py | infrastructure | PARTIALLY_INTEGRATED | 1 | First-class project entities for UMH | Unique — project registry |
| runtime_fleet.py | world-model | PARTIALLY_INTEGRATED | 2 | Runtime fleet model — provider tracking and selection | Unique — fleet model |
| runtime_state_registry.py | infrastructure | PARTIALLY_INTEGRATED | 2 | Live environment awareness for the workstation | Unique — runtime state |
| runtime_handoff.py | execution | PARTIALLY_INTEGRATED | 1 | Bridges Work Packets to runtime sessions | Unique — packet→session bridge |
| runtime_awareness_runtime.py | self-model | PARTIALLY_INTEGRATED | 1 | Unified view of active system state | Unique — runtime awareness |
| operational_truth.py | self-model | PARTIALLY_INTEGRATED | 2 | OperationalTruthSnapshot — scoreboard for UMH operational reality | Unique — operational snapshot |
| operationalization_runtime.py | learning | PARTIALLY_INTEGRATED | 1 | Link capabilities to reusable artifacts | Unique — operationalization |
| infrastructure_runtime.py | infrastructure | PARTIALLY_INTEGRATED | 1 | Register and track system & institutional infrastructure | Unique — infra registry |
| knowledge_awareness_runtime.py | understanding | PARTIALLY_INTEGRATED | 1 | Meaning, not just documents — knowledge-level awareness | Unique — semantic awareness |
| documentation_awareness_runtime.py | perception | PARTIALLY_INTEGRATED | 1 | Content-level metadata for docs | Unique — doc awareness |
| repository_awareness_runtime.py | perception | PARTIALLY_INTEGRATED | 1 | File-level depth for repositories | Unique — repo awareness |

---

## Dormant (zero or near-zero importers, unreachable from production)

| File | Capability | Status | Importers | Unique Contribution | Canonical? |
|------|-----------|--------|-----------|---------------------|-----------|
| operator_loop_runtime.py | coordination | DORMANT | 0 | "The Jarvis Runtime" — 7-method operator API | ORPHANED — never integrated |
| operator_loop_coordinator.py | coordination | DORMANT | 2 | End-to-end operator acceptance loop | ORPHANED — phase 13.4 |
| operating_loop_coherence_runtime.py | governance | DORMANT | 1 | Coherence checking across all loops | ORPHANED — unique but unwired |
| orchestration_loop.py | coordination | DORMANT | 2 | Persistent autonomous execution — alternative daemon loop model | SUPERSEDED by AutonomousTick |
| organism_loop.py | execution | DORMANT | 3 | Convergence coordinator for organism execution | SUPERSEDED by GovernedExecutionSpine |
| operator_escape_tracker.py | perception | DORMANT | 0 | Records exits from UMH organism | ORPHANED — never integrated |
| operator_migration_runtime.py | coordination | DORMANT | 1 | Track and close external-loop dependencies | ORPHANED |
| sandbox_orchestrator.py | execution | DORMANT | 0 | Ties approval gate to PR factory execution | ORPHANED |
| self_maintenance_bridge.py | recovery | DORMANT | 0 | Wires degradation detection to work packet creation | ORPHANED — unique bridge concept |
| deploy_verification_worker.py | governance | DORMANT | 0 | "No human should discover a white screen" post-deploy check | ORPHANED — unique but unwired |
| correspondence_scheduler.py | governance | DORMANT | 0 | Periodic drift detection scheduling for projections | ORPHANED |
| benchmark_harness.py | learning | DORMANT | 0 | Legacy pipeline comparison harness | OBSOLETE |
| source_truth_linker.py | understanding | DORMANT | 0 | Cross-domain edge builder for Reality Graph | ORPHANED — unique but unwired |
| mutation_catalog.py | governance | DORMANT | 0 | Maps HTTP endpoints to MutationSpec names | ORPHANED |
| daily_driver_log.py | learning | DORMANT | 0 | Records unhandled failures during real operation | ORPHANED — H5 creation, never wired to consumers |
| action_voice_contract.py | perception | DORMANT | 0 | Voice/Intent action contract | ORPHANED |
| environment_discovery.py | perception | DORMANT | 1 | Device, filesystem, application, account inventory | Unique but orphaned |

---

## Backward-Compatibility Shims (OBSOLETE)

| File | Capability | Status | Unique Contribution | Canonical? |
|------|-----------|--------|---------------------|-----------|
| dex_conversation.py | — | OBSOLETE | Shim → advisor_conversation.py | No — use advisor_conversation |
| dex_reconciliation.py | — | OBSOLETE | Shim → advisor_reconciliation.py | No — use advisor_reconciliation |

---

## Subdirectories

### audits/ (7 files)

| File | Capability | Status | Importers | Unique Contribution |
|------|-----------|--------|-----------|---------------------|
| __init__.py | infrastructure | — | — | Package init |
| context_capacity.py | self-model | DORMANT | 0 | Context capacity audit — measures context window usage |
| empire_readiness.py | governance | DORMANT | 0 | Empire readiness audit |
| model_correspondence.py | self-model | DORMANT | 0 | Predicted state vs observed reality correspondence |
| operational_awareness.py | self-model | DORMANT | 0 | Operational awareness audit |
| organism_awareness.py | self-model | DORMANT | 0 | Organism self-awareness audit |
| source_truth.py | understanding | DORMANT | 0 | Source of truth production lineage audit |

### benchmarks/ (24 files)

| File | Capability | Status | Importers | Unique Contribution |
|------|-----------|--------|-----------|---------------------|
| __init__.py | infrastructure | — | — | Package init |
| autonomous_execution.py | learning | DORMANT | 0 | Benchmark: session depth, recovery, independence |
| capability_reuse.py | learning | DORMANT | 0 | Benchmark: capability reuse (dual-track) |
| company_ops.py | learning | DORMANT | 0 | Benchmark F: company operations for C33 |
| competitive.py | prediction | PARTIALLY_INTEGRATED | 2 | Competitive benchmarking — profiles, categories, scoring |
| composite_scorer.py | learning | PARTIALLY_INTEGRATED | 1 | Aggregate 20 categories into competitive matrix |
| compounding_proof.py | learning | DORMANT | 0 | Benchmark 7: compounding proof integration |
| efficiency.py | learning | DORMANT | 0 | Benchmark: capability per dollar |
| external_adapters.py | learning | PARTIALLY_INTEGRATED | 1 | Industry-standard benchmarks through UMH |
| governance_quality.py | governance | DORMANT | 0 | Benchmark D: governance quality for C33 |
| harness_scorer.py | learning | DORMANT | 0 | C29 harness superiority scoring engine |
| harness_superiority.py | learning | PARTIALLY_INTEGRATED | 1 | C29 harness superiority data model and registry |
| human_amplification.py | learning | DORMANT | 0 | Benchmark: does the operator become more capable? |
| mutation_equivalence.py | governance | DORMANT | 0 | Benchmark H: mutation equivalence for C33 |
| operator_compression.py | learning | DORMANT | 0 | Benchmark 5: operator compression |
| orchestration_quality.py | coordination | DORMANT | 0 | Benchmark C: orchestration quality for C33 |
| outcome_accuracy.py | learning | DORMANT | 0 | Benchmark: did completed work achieve intent? |
| production_outcome_quality.py | learning | DORMANT | 0 | Benchmark 6: production outcome quality |
| production_quality.py | learning | DORMANT | 0 | Benchmark 2: production quality |
| production_velocity.py | learning | DORMANT | 0 | Benchmark 3: production velocity |
| projection_readiness.py | governance | PARTIALLY_INTEGRATED | 2 | Benchmark: projection readiness |
| reality_correspondence.py | learning | PARTIALLY_INTEGRATED | 1 | 50 failure scenarios across 5 domains |
| reality_recovery.py | recovery | DORMANT | 0 | Benchmark 1: reality recovery |
| reliability.py | learning | DORMANT | 0 | Benchmark: consistency across repeated builds |
| strategic_compression.py | learning | DORMANT | 0 | Benchmark: high-level intent to executable reality |
| surface_switching.py | learning | DORMANT | 0 | Surface switching cost tracker |

### executors/ (5 files)

| File | Capability | Status | Importers | Unique Contribution |
|------|-----------|--------|-----------|---------------------|
| __init__.py | execution | — | — | Package init |
| agent_executor.py | execution | PARTIALLY_INTEGRATED | 2 | First governed LLM/Claude Code executor (Phase 17A) |
| approval_intercept.py | governance | TRANSITIVE_ACTIVE | 10 | Runtime human-in-the-loop governance for executors |
| execution_telemetry.py | reflection | TRANSITIVE_ACTIVE | 8 | Live event pipeline for executor lifecycle |
| workstation_executor.py | execution | PARTIALLY_INTEGRATED | 1 | First production ExecutorContract implementation |

### self_use/ (7 files)

| File | Capability | Status | Importers | Unique Contribution |
|------|-----------|--------|-----------|---------------------|
| __init__.py | governance | — | — | Package init — C27 daily driver readiness |
| certification_report.py | governance | PARTIALLY_INTEGRATED | 2 | 4-gate pass/fail with coherence override |
| gap_ledger.py | self-model | PARTIALLY_INTEGRATED | 2 | Structured log of friction points, missing capabilities, failures |
| meta_ide_audit.py | governance | PARTIALLY_INTEGRATED | 2 | Manual operator testing of every subsystem |
| projection_delta.py | self-model | PARTIALLY_INTEGRATED | 2 | Desired vs implemented vs certified delta |
| task_catalog.py | governance | PARTIALLY_INTEGRATED | 2 | C27 self-use certification task management |
| task_taxonomy.py | governance | PARTIALLY_INTEGRATED | 3 | Domain classification for self-use certification |

---

## Summary Statistics

| Category | Count |
|----------|-------|
| PRODUCTION_ACTIVE (daemon direct) | 55 |
| TRANSITIVE_ACTIVE | ~50 |
| PARTIALLY_INTEGRATED | ~130 |
| DORMANT | ~30 |
| OBSOLETE | 2 |
| **Total organism modules** | **~267** |

## Key Fragmentation Findings

### Duplicate/Overlapping Modules

1. **Governance execution paths** (3 overlapping):
   - `governed_spine.py` — THE canonical mutation gateway ✓
   - `governed_execution_runtime.py` — Campaign 16.0 alternative
   - `governed_work_runtime.py` — mandatory execution gateway duplicate

2. **Coordination/orchestration** (4 overlapping):
   - `coordinator.py` — canonical task decomposition ✓
   - `execution_coordinator.py` — Phase 13 alternative
   - `organism_coordination_engine.py` — C15.1 alternative
   - `orchestrator_kernel.py` — operator routing

3. **Execution journals** (2):
   - `execution_journal.py` — canonical ✓
   - `execution_ledger.py` — parallel ledger

4. **Learning/compounding** (2):
   - `capability_compounding_runtime.py` — C22.4
   - `compounding_engine.py` — earlier version

5. **Memory** (3 in organism alone):
   - `memory_promotion.py` — daemon-active ✓
   - `institutional_memory_runtime.py` — knowledge lifecycle
   - `strategic_memory_engine.py` — timeline snapshots

6. **Loop architectures** (4):
   - daemon.py + autonomous_tick.py — canonical ✓
   - `orchestration_loop.py` — superseded
   - `organism_loop.py` — superseded
   - `strategic_tick_loop.py` — partially used alternative

7. **Proof** (2):
   - `proof_store.py` — canonical ✓
   - `proof_runtime.py` — overlapping

### Unique Capabilities at Risk (DORMANT but valuable)

1. `operating_loop_coherence_runtime.py` — coherence checking across all loops
2. `self_maintenance_bridge.py` — wires degradation→work packet creation
3. `deploy_verification_worker.py` — post-deploy white screen detection
4. `source_truth_linker.py` — cross-domain edge builder for Reality Graph
5. `daily_driver_log.py` — unhandled failure tracking (H5, needs consumers)
6. `operator_escape_tracker.py` — records exits from UMH
