---
type: codewiki-inventory
dir: tests
source_sha: c806e75e29acfc82d1428de2ccc17924403407ab
---

# `tests/` — File Inventory

**Files:** 449 regular + 0 symlinks · **Bytes:** 6,622,193

[Narrative page](../dirs/tests.md)


## tests/ (root)

| Path | Lines | Purpose |
|---|---|---|
| `tests/__init__.py` | 0 | package marker (empty) |
| `tests/conftest.py` | 12 | — |
| `tests/phase13_2_runtime_proofs.py` | 631 | Phase 13.2 runtime surface proofs — lifecycle, stop/cancel, policy blocks. |
| `tests/test_actuator_bridge.py` | 119 | Tests for Layer 3 Phase 2 Slice D: ActuatorMaturityLevel ↔ AdapterMaturityLevel bridge. |
| `tests/test_adaptercall_token_seam.py` | 241 | Tests — WP-P4-ADAPTERCALL-TOKEN-SEAM-001. |
| `tests/test_agent_executor.py` | 726 | Tests for AgentExecutor — Phase 17A. |
| `tests/test_agent_fleet_runtime.py` | 519 | Tests for W3 — Agent Fleet Runtime. |
| `tests/test_agent_workforce_runtime.py` | 277 | Tests for AgentWorkforceRuntime — Campaign 19.1. |
| `tests/test_approval_intercepts.py` | 805 | Phase 15C: Approval Intercepts — comprehensive test suite. |
| `tests/test_approval_request_canonical.py` | 186 | WP-P1-007 — canonical ApprovalRequest type + round-trip adapter tests. |
| `tests/test_artifact_registry.py` | 363 | Tests for Campaign 6.0 — Artifact Registry. |
| `tests/test_assumption_tracking_runtime.py` | 265 | Tests for Campaign 9.2 — Assumption Tracking Runtime. |
| `tests/test_attention_aggregation_runtime.py` | 237 | Tests for AttentionAggregationRuntime — Campaign 18.2. |
| `tests/test_authority_tier.py` | 291 | Tests for authority tier propagation through the ingestion pipeline. |
| `tests/test_browser_wiring.py` | 97 | Tests for browser control wiring to department agents. |
| `tests/test_c16_integration.py` | 365 | Integration tests for Campaign 16 — Governed Execution Loop. |
| `tests/test_c18_integration.py` | 208 | Integration tests for Campaign 18 — Jarvis Experience Validation (C18.5). |
| `tests/test_c19_integration.py` | 365 | Integration tests for Campaign 19 — Execution Fabric & Agent Operations. |
| `tests/test_c20_0_voice_ingress.py` | 351 | Tests for Campaign 20.0 — Voice Ingress Runtime. |
| `tests/test_c20_1_voice_session_manager.py` | 375 | Tests for Campaign 20.1 — Voice Session Manager. |
| `tests/test_c20_2_ambient_wake.py` | 236 | Tests for Campaign 20.2 — Ambient Wake Runtime. |
| `tests/test_c20_3_voice_output.py` | 183 | Tests for Campaign 20.3 — Voice Output Runtime. |
| `tests/test_c20_4_voice_operations.py` | 461 | Tests for Campaign 20.4 — Voice Operations Runtime. |
| `tests/test_c20_integration.py` | 434 | Integration tests for Campaign 20 — Voice Operations & Ambient Jarvis. |
| `tests/test_c21_0_screen_awareness_runtime.py` | 253 | Tests for ScreenAwarenessRuntime — Campaign 21.0. |
| `tests/test_c21_1_environment_awareness.py` | 236 | Tests for EnvironmentAwarenessRuntime — Campaign 21.1. |
| `tests/test_c21_2_visual_context.py` | 300 | Tests for C21.2 — Visual Context Runtime. |
| `tests/test_c21_3_attention_vision.py` | 360 | Tests for AttentionVisionRuntime — Campaign 21.3. |
| `tests/test_c21_4_visual_operations.py` | 450 | Tests for VisualOperationsRuntime — Campaign 21.4. |
| `tests/test_c21_integration.py` | 322 | Integration tests for Campaign 21 — Visual Awareness. |
| `tests/test_c22_acceptance.py` | 492 | Acceptance tests for Campaign 22 — Software Production Organism. |
| `tests/test_c22_capability_compounding.py` | 630 | Tests for CapabilityCompoundingRuntime — Campaign 22.4 |
| `tests/test_c22_product_factory.py` | 712 | Tests for C22.5 — Product Factory Runtime. |
| `tests/test_c22_production_ops_runtime.py` | 683 | Tests for C22.0 — Production Operations Runtime. |
| `tests/test_c22_production_planning.py` | 573 | Tests for C22.1 — Production Planning Runtime. |
| `tests/test_c22_production_review.py` | 690 | Tests for C22.3 — Production Review Runtime. |
| `tests/test_c22_production_routes.py` | 292 | Tests for C22.7 — Production Surface Routes. |
| `tests/test_c22_production_workforce.py` | 602 | Tests for Campaign 22.2 — Production Workforce Runtime. |
| `tests/test_c22_source_truth.py` | 713 | Tests for C22.6 — Source Truth Runtime (CORE DELIVERABLE). |
| `tests/test_c23a_benchmarks.py` | 587 | Tests for C23A benchmarks 2-7 + projection readiness. |
| `tests/test_c23a_capability_reuse.py` | 170 | Tests for Benchmark 4 — Capability Reuse (Dual-Track). |
| `tests/test_c23a_capability_validation_runtime.py` | 412 | Tests for CapabilityValidationRuntime — C23A Phase 1. |
| `tests/test_c23a_compounding_proof.py` | 236 | Tests for Compounding Proof Benchmark — C23A Phase 8. |
| `tests/test_c23a_operator_compression.py` | 197 | Tests for Benchmark 5 — Operator Compression. |
| `tests/test_c23a_production_outcome_quality.py` | 217 | Tests for Benchmark 6 — Production Outcome Quality. |
| `tests/test_c23a_production_quality.py` | 194 | Tests for Benchmark 2 — Production Quality. |
| `tests/test_c23a_production_velocity.py` | 172 | Tests for Benchmark 3 — Production Velocity. |
| `tests/test_c23a_projection_readiness.py` | 182 | Tests for Projection Readiness Benchmark — C23A Phase 9. |
| `tests/test_c23a_reality_recovery.py` | 194 | Tests for Reality Recovery Benchmark — C23A Phase 2. |
| `tests/test_c23b_competitive.py` | 291 | Tests for Campaign 23B competitive data layer and composite scorer. |
| `tests/test_c23b_composite_scorer.py` | 291 | Tests for Campaign 23B composite scorer and routes. |
| `tests/test_c23b_external_adapters.py` | 224 | Tests for Campaign 23B external benchmark adapters. |
| `tests/test_c23b_organism_audits.py` | 675 | Tests — Campaign 23B organism audits (Tier 3). |
| `tests/test_c23b_production_benchmarks.py` | 367 | Tests for Campaign 23B production benchmarks (B, N, Q, R). |
| `tests/test_c23b_strategic_metrics.py` | 620 | Campaign 23B — Strategic Metrics test suite. |
| `tests/test_c31_phase6.py` | 254 | C31 Phase 6 — Daily Driver Operationalization tests. |
| `tests/test_c31_phase7.py` | 250 | C31 Phase 7: Verification & Campaign Closure tests. |
| `tests/test_c31_spine_learning.py` | 152 | Tests for C31 Phase 5: spine → learning loop integration. |
| `tests/test_c32_benchmark.py` | 135 | C32 Benchmark Harness Tests. |
| `tests/test_c32_cycle1_legacy.py` | 120 | C32 Cycle 1 — Pipeline A (Legacy) tests. |
| `tests/test_c32_cycles.py` | 216 | C32 Benchmark Cycle Tests — Cycles 2-5. |
| `tests/test_c32_pipeline_b.py` | 297 | C32 Pipeline B Integration Tests. |
| `tests/test_c33_benchmarks.py` | 551 | C33 Phase 1 benchmark infrastructure tests. |
| `tests/test_c33_phase0.py` | 330 | C33 Phase 0 exit gate tests — verify D1-D4 fixes work end-to-end. |
| `tests/test_c33_phase1.py` | 445 | C33 Phase 1 exit gate tests — verify benchmark infrastructure works. |
| `tests/test_c34_mutation_router.py` | 637 | C34 Phase 1-2 tests: MutationRegistry extensions, MutationRouter, MutationCatalog. |
| `tests/test_c35_qualification.py` | 566 | C35 Organism Qualification Tests. |
| `tests/test_c36_qualification.py` | 573 | C36 Qualification System Maturation Tests. |
| `tests/test_c37_self_model_predictor.py` | 519 | Tests for C37 — PredictiveSelfModel with Welford variance and hierarchical keys. |
| `tests/test_c38_predictive_optimization.py` | 406 | C38 Qualification-Driven Optimization Tests. |
| `tests/test_c39_live_simulation.py` | 355 | C39 — Live Gap-Closure Simulation Tests. |
| `tests/test_c40a_runtime_convergence.py` | 393 | C40A — Surface Runtime Convergence Tests. |
| `tests/test_c40b_embodiment.py` | 525 | C40B — Runtime Embodiment Campaign tests. |
| `tests/test_canonical_memory_reconciliation_v1.py` | 372 | Tests for canonical memory reconciliation engine. |
| `tests/test_canonical_voice_runtime.py` | 53 | P4S31 Voice Convergence — the canonical voice runtime declaration. |
| `tests/test_capability_catalog_slice_a.py` | 228 | Tests for Layer 3 Phase 3 Slice A — Capability Catalog + TME Orchestrator. |
| `tests/test_capability_evolution_engine.py` | 227 | Tests for CapabilityEvolutionEngine — Campaign 12.2. |
| `tests/test_capability_extraction_slice_b.py` | 341 | Tests for Layer 3 Phase 3 Slice B — LLM capability extraction. |
| `tests/test_capability_gap_engine.py` | 367 | Campaign 10.1 — Capability Gap Engine tests. |
| `tests/test_capability_graph_engine.py` | 246 | Campaign 10.0 — Capability Graph Engine tests. |
| `tests/test_capability_intelligence_integration.py` | 213 | Campaign 10 — Capability Intelligence integration tests. |
| `tests/test_capability_portfolio_runtime.py` | 273 | Campaign 10.2 — Capability Portfolio Runtime tests. |
| `tests/test_cc_webhook_auth.py` | 207 | WP-P0-004 — CC webhook receiver auth + loopback-bind regression tests. |
| `tests/test_cli_voice_command.py` | 93 | P4S31 Voice Convergence — CLI /voice push-to-talk (Commit 6). |
| `tests/test_cockpit_capability_map.py` | 255 | Tests for CockpitCapabilityMap — Campaign 3.1. |
| `tests/test_cockpit_endpoints.py` | 153 | Tests for cockpit API additions: activity stream, governance controls, DEX channel. |
| `tests/test_cockpit_voice_message_playable.py` | 58 | P4S31 — playable voice messages (iMessage/Instagram/Telegram-style). |
| `tests/test_cockpit_voice_wire.py` | 760 | P4S31 Voice Convergence — cockpit capture edges speak the governed protocol. |
| `tests/test_command_center_mvp_runtime.py` | 541 | Tests for CommandCenterMVPRuntime — Campaign 3.2. |
| `tests/test_command_runtime.py` | 856 | Tests for Phase 9 — Command Runtime. |
| `tests/test_compute_fabric_runtime.py` | 519 | Tests for W1 — Unified Compute Fabric Runtime. |
| `tests/test_conference_rooms.py` | 1,059 | Tests for Conference Rooms — servers, categories, channels, messages, threads, |
| `tests/test_context_assembler.py` | 112 | Tests for ConcreteContextAssembler. |
| `tests/test_context_resolution.py` | 353 | Tests for Context Resolution Engine — Campaign 5.5. |
| `tests/test_context_resolution_v2.py` | 670 | Tests for Campaign 6.5 — Context Resolution V2 (Operational Reality). |
| `tests/test_continuity_runtime.py` | 817 | Tests for Phase 7: Continuity Runtime. |
| `tests/test_convergence_acceptance.py` | 152 | End-to-end acceptance tests for the converged UMH substrate. |
| `tests/test_correspondence_ledger.py` | 345 | C26D — Correspondence Ledger tests. |
| `tests/test_daemon_e2e.py` | 414 | End-to-end integration test — real NodeMeshServer + real NodeClient. |
| `tests/test_decision_impact_engine.py` | 391 | Tests for Campaign 9.5 — Decision Impact Engine. |
| `tests/test_decision_lineage_engine.py` | 362 | Tests for Campaign 9.1 — Decision Lineage Engine. |
| `tests/test_decision_registry.py` | 361 | Tests for Campaign 9.0 — Decision Registry. |
| `tests/test_decision_validity_engine.py` | 530 | Tests for Campaign 9.3 — Decision Validity Engine. |
| `tests/test_decomposer_depth.py` | 365 | Tests for decomposer depth upgrade — semantic extraction quality. |
| `tests/test_delegation_readiness_runtime.py` | 416 | Tests for DelegationReadinessRuntime — Campaign 11.1. |
| `tests/test_delegation_runtime.py` | 382 | Tests for Campaign 4.7 — Delegation Runtime. |
| `tests/test_deploy_verification_worker.py` | 316 | Tests for C26B — Deploy Verification Worker. |
| `tests/test_device_awareness.py` | 319 | Tests for Device Awareness Runtime — Campaign 5.3. |
| `tests/test_device_presence.py` | 170 | Tests for substrate/workstation/device_presence.py. |
| `tests/test_discord_hot_path_smoke.py` | 118 | Smoke test: Discord → Gateway → CognitiveLoop → ModelRouter → Governance. |
| `tests/test_documentation_awareness.py` | 351 | Tests for Campaign 6.2 — Documentation Awareness Runtime. |
| `tests/test_domain_bridge.py` | 285 | Tests for ontology-domain bridge — business as first domain projection. |
| `tests/test_domain_bridge_life_creator.py` | 722 | Tests for life and creator domain bridges. |
| `tests/test_domain_stores_tier3.py` | 177 | Structural tests for all 14 Tier 3 domain store classes. |
| `tests/test_drift_detection_engine.py` | 327 | Campaign 7.4 — Drift Detection Engine tests. |
| `tests/test_embodiment_runtime.py` | 354 | Tests for W4 — Embodiment Runtime. |
| `tests/test_empire_engine.py` | 456 | Empire WorkPacket Engine — Phase 3 tests. |
| `tests/test_entity_link_store.py` | 31 | Structural tests for EntityLinkStore. |
| `tests/test_eos_action_decisions.py` | 519 | WP-P4-EOS-ACTION-APPROVAL-COMMAND-001 — governed approve/reject seam tests. |
| `tests/test_eos_action_execution.py` | 524 | WP-P4-EOS-EXECUTOR-ACTIVATE-001 — approved non-provider execution tests. |
| `tests/test_eos_action_executor_seam.py` | 265 | WP-P4-EOS-ACTION-EXECUTOR-SEAM-001 — action-executor seam map regression tests. |
| `tests/test_eos_action_proposals_read.py` | 496 | WP-P4-EOS-ACTION-PROPOSAL-READ-001 — EOS ActionProposal read seam tests. |
| `tests/test_eos_activation_slice.py` | 215 | WP-P4-006 — EOS projection activation/readiness slice. |
| `tests/test_eos_app_module_map.py` | 213 | WP-P4-EOS-APP-MODULE-MAP-001 — EOS app-body module map regression tests. |
| `tests/test_eos_boot_contract.py` | 77 | WP-P4-003 — EOS integration boot-contract regression tests. |
| `tests/test_eos_poller_watermark_boundary.py` | 104 | WP-P4-005 — EOS poller watermark adapter-boundary + behavior regression. |
| `tests/test_eos_projection.py` | 63 | Tests for EOS projection entry point. |
| `tests/test_eos_tenant_isolation.py` | 119 | Tenant-isolation regression test for EOS task polling (WP-P0-010). |
| `tests/test_execution_authority_engine_v1.py` | 658 | Tests for Execution Authority Engine v1. |
| `tests/test_execution_coordinator.py` | 1,023 | Tests for Phase 13: Execution Coordinator Runtime. |
| `tests/test_execution_fabric_runtime.py` | 325 | Tests for ExecutionFabricRuntime — Campaign 19.0. |
| `tests/test_execution_lifecycle_runtime.py` | 393 | Tests for Execution Lifecycle Runtime — Campaign 16.2. |
| `tests/test_execution_telemetry.py` | 718 | Tests for Execution Telemetry — Phase 15B. |
| `tests/test_executive_brief_runtime.py` | 490 | Campaign 7.5 — Executive Brief Runtime tests. |
| `tests/test_executive_portfolio_runtime.py` | 356 | Tests for ExecutivePortfolioRuntime — Campaign 14.2. |
| `tests/test_executive_routes.py` | 105 | Tests for cockpit executive routes — Campaign 14.3. |
| `tests/test_executor_runtime.py` | 1,105 | Tests for Phase 14 — Executor Runtime. |
| `tests/test_feedback_capture.py` | 138 | Tests for ConcreteFeedbackCapture. |
| `tests/test_gap_closures.py` | 180 | Tests for the 3 final gap closures: companies endpoint, skill allocation, ingestion facade. |
| `tests/test_gate10_projection_consumption.py` | 311 | Tests for Gate 10 — Projection Consumption Layer. |
| `tests/test_gate3_governed_work_runtime.py` | 1,129 | Gate 3 — Governed Work Runtime — test suite. |
| `tests/test_gate4_intent_runtime.py` | 803 | Tests for Gate 4 — IntentRuntime (Workstation Convergence). |
| `tests/test_gate4_workstation_convergence.py` | 677 | Gate 4 — Workstation Convergence Runtime — Validation Tests. |
| `tests/test_gate5_capability_runtime.py` | 581 | Gate 5 — Capability Runtime tests. |
| `tests/test_gate6_operationalization_runtime.py` | 478 | Gate 6 — Operationalization Runtime tests. |
| `tests/test_gate7_infrastructure_runtime.py` | 342 | Tests for Gate 7 — Infrastructure Runtime. |
| `tests/test_gate8_execution_graph.py` | 527 | Tests for Gate 8 — Execution Graph (lineage validation). |
| `tests/test_gate9_compounding_engine.py` | 383 | Tests for Gate 9 — Capability Compounding Engine. |
| `tests/test_generic_ingestion_orchestrator.py` | 175 | Tests for the generic ingestion orchestrator. |
| `tests/test_goal_alignment_engine.py` | 478 | Tests for GoalAlignmentEngine — Campaign 8.4. |
| `tests/test_goal_drift_engine.py` | 591 | Tests for GoalDriftEngine — Campaign 8.5. |
| `tests/test_goal_hierarchy_engine.py` | 344 | Goal Hierarchy Engine — Campaign 8.1 tests. |
| `tests/test_governance_full.py` | 154 | Tests for GovernanceEngine — risk classification and execution authority. |
| `tests/test_governance_routes.py` | 90 | Tests for cockpit governance routes — Campaign 15.4. |
| `tests/test_governance_runtime.py` | 258 | Tests for Governance Runtime — Campaign 15.0. |
| `tests/test_governed_execution_runtime.py` | 347 | Tests for Governed Execution Runtime — Campaign 16.0. |
| `tests/test_governed_mutation_fail_closed.py` | 416 | WP-P0-001 — Fail-closed governed_mutation() regression tests. |
| `tests/test_grounding_firewall.py` | 691 | Tests for Phase 14.14C — Grounding Firewall + Hermes + Vision. |
| `tests/test_gws_source.py` | 168 | Tests for GWSSource — Google Workspace ingestion source adapter. |
| `tests/test_gws_to_canonical_ingestion_v1.py` | 226 | Tests for GWS-to-canonical-substrate ingestion pipeline. |
| `tests/test_harness_scorer.py` | 809 | C29 Harness Superiority — scoring engine tests. |
| `tests/test_harness_superiority.py` | 1,014 | C29 Harness Superiority — data model tests. |
| `tests/test_hermes_adapter_parity.py` | 585 | Tests for Phase 14.14E — Hermes Adapter Parity. |
| `tests/test_identity_resolver.py` | 91 | Tests for ConcreteIdentityResolver. |
| `tests/test_import_smoke_router_environments.py` | 91 | Import-smoke tests for modules whose symbol renames have repeatedly |
| `tests/test_institutional_memory_runtime.py` | 261 | Tests for InstitutionalMemoryRuntime — Campaign 15.2. |
| `tests/test_interpretation_engine_v1.py` | 586 | Tests for Interpretation Engine v1 — Phase 96.8W. |
| `tests/test_knowledge_awareness.py` | 310 | Tests for Campaign 6.4 — Knowledge Awareness Runtime. |
| `tests/test_knowledge_layers.py` | 151 | — |
| `tests/test_learning_extraction_runtime.py` | 223 | Tests for LearningExtractionRuntime — Campaign 12.0. |
| `tests/test_learning_portfolio_runtime.py` | 255 | Tests for LearningPortfolioRuntime — Campaign 12.3. |
| `tests/test_learning_routes.py` | 91 | Tests for cockpit learning routes — Campaign 12.4. |
| `tests/test_live_runtime_identity_v1.py` | 302 | Tests for Phase 96.8AK — Live Runtime Identity and Git Parity. |
| `tests/test_lyfeos_creatoros_integration.py` | 490 | Tests for EOS, LyfeOS, and CreatorOS integration adapters — protocol conformance and signal building. |
| `tests/test_memory_api_tier2.py` | 39 | Tests for Law 5.5 Tier 2 — merge_event_payload() method. |
| `tests/test_memory_system.py` | 110 | Tests for ConcreteMemorySystem. |
| `tests/test_mesh_auth_binding.py` | 154 | Mesh trust boundary — WS auth, token→node binding, header transport, relay read auth. |
| `tests/test_mesh_dispatch_contract.py` | 209 | C40A Phase 2 — Mesh Dispatch Contract Tests. |
| `tests/test_mesh_dispatch_governed.py` | 438 | Mesh trust boundary — fail-closed relay, verdict required + validated, governed dispatch. |
| `tests/test_meta_ide_audit.py` | 226 | Tests for Meta IDE functional audit. |
| `tests/test_meta_ide_context_runtime.py` | 189 | Tests for Campaign 17.1 — MetaIdeContextRuntime. |
| `tests/test_meta_ide_projection_loop_runtime.py` | 325 | Tests for MetaIDEProjectionLoopRuntime — Campaign 3.4. |
| `tests/test_meta_ide_runtime.py` | 366 | Tests for W2 — Meta IDE Runtime. |
| `tests/test_mvp_readiness_runtime.py` | 334 | Tests for MVPReadinessRuntime — Campaign 4.5. |
| `tests/test_native_voice_permissions.py` | 56 | P4S31 Voice Convergence — native mic permissions + runtime-derived identity (Commit 6). |
| `tests/test_node_mesh.py` | 387 | Node mesh integration tests — verifies the full VPS-side stack. |
| `tests/test_node_mesh_ws.py` | 186 | WebSocket integration test — simulates a node connecting to the mesh server. |
| `tests/test_notification_engine.py` | 217 | Tests for substrate.sockets.notification_engine. |
| `tests/test_ontology_enacted.py` | 198 | Tests for substrate.ontology — primitives, laws, and domain bridges. |
| `tests/test_ontology_home_map.py` | 287 | WP-P3 — ontology-home consolidation tests. |
| `tests/test_ontology_layer_contract.py` | 191 | WP-P3-001 — ontology/metamodel layer contract tests. |
| `tests/test_operating_loop_coherence_runtime.py` | 547 | Tests for OperatingLoopCoherenceRuntime — Campaign 4.3. |
| `tests/test_operating_loop_runtime.py` | 353 | Tests for OperatingLoopRuntime — Campaign 4.1. |
| `tests/test_operations_routes.py` | 105 | Tests for Operations API routes — Campaign 19.3. |
| `tests/test_operator_api_mounts_voice.py` | 47 | P4S31 Voice Convergence — operator_api mounts the governed voice router (Commit 3). |
| `tests/test_operator_api_voice_preload.py` | 47 | P4S31 Voice Convergence — operator_api warm-engine preload (Commit 3). |
| `tests/test_operator_loop_mvp.py` | 356 | Operator Loop MVP — end-to-end integration test. |
| `tests/test_operator_loop_phase2.py` | 309 | Operator Loop Phase 2 — Autonomous Implementation tests. |
| `tests/test_operator_migration_runtime.py` | 318 | Tests for W5 — Operator Migration Runtime. |
| `tests/test_orchestrator_awareness_runtime.py` | 680 | Tests for OrchestratorAwarenessRuntime — Campaign 4.0. |
| `tests/test_orchestrator_presence_runtime.py` | 241 | Tests for Campaign 17.0 — OrchestratorPresenceRuntime. |
| `tests/test_organism_coordination_engine.py` | 278 | Tests for Organism Coordination Engine — Campaign 15.1. |
| `tests/test_organism_portfolio_runtime.py` | 287 | Tests for OrganismPortfolioRuntime — Campaign 15.3. |
| `tests/test_organism_state_runtime.py` | 246 | Tests for Organism State Runtime — Campaign 16.1. |
| `tests/test_outcome_pattern_engine.py` | 246 | Tests for OutcomePatternEngine — Campaign 12.1. |
| `tests/test_outcome_tracking_runtime.py` | 312 | Tests for OutcomeTrackingRuntime — Campaign 8.2. |
| `tests/test_outcome_verification.py` | 525 | Tests for C26A — Outcome Verification Runtime. |
| `tests/test_override_tracking.py` | 255 | Tests for override outcome tracking in HomeostasisEngine. |
| `tests/test_p0_smoke.py` | 177 | P0 smoke tests — fast import/health checks for all production services. |
| `tests/test_p1_phase10_transports.py` | 79 | P1 Phase 10 — Transport Layer Convergence tests. |
| `tests/test_p1_phase11_adapters.py` | 94 | P1 Phase 11 — Adapter Layer Convergence tests. |
| `tests/test_p1_phase12_projections.py` | 80 | P1 Phase 12 — Projections & Nodes Convergence tests. |
| `tests/test_p1_phase13_services.py` | 108 | P1 Phase 13 — Services, Scripts & Tests Convergence tests. |
| `tests/test_p1_phase14_cockpit.py` | 70 | P1 Phase 14 — Cockpit UI Convergence tests. |
| `tests/test_p1_phase2_bridge.py` | 278 | P1 Phase 2 — Cognitive Pipeline Bridge tests. |
| `tests/test_p1_phase2b_operator.py` | 209 | P1 Phase 2B — Operator Experience Layer verification. |
| `tests/test_p1_phase3_memory.py` | 155 | P1 Phase 3 — Memory Convergence tests. |
| `tests/test_p1_phase4_world_model.py` | 149 | P1 Phase 4 — World Model Convergence tests. |
| `tests/test_p1_phase5_reasoning.py` | 191 | P1 Phase 5 — Reasoning Integration tests. |
| `tests/test_p1_phase6_learning.py` | 166 | P1 Phase 6 — Learning Integration tests. |
| `tests/test_p1_phase7_loops.py` | 72 | P1 Phase 7 — Autonomous Operation tests. |
| `tests/test_p1_phase8_closure.py` | 102 | P1 Phase 8 — Capability Closure tests. |
| `tests/test_p1_phase9_architecture.py` | 234 | P1 Phase 9 — Architecture Law Enforcement tests. |
| `tests/test_p2_phase1_runner.py` | 304 | P2 Phase 1 — WorkflowRunner tests. |
| `tests/test_p2_phase2_research.py` | 128 | P2 Phase 2 — Research Workflow tests. |
| `tests/test_p2_phase3_planning.py` | 125 | P2 Phase 3 — Planning Workflow tests. |
| `tests/test_p2_phase4_communication.py` | 166 | P2 Phase 4 — Communication Workflow tests. |
| `tests/test_p2_phase5_review.py` | 116 | P2 Phase 5 — Review Workflow tests. |
| `tests/test_p2_phase6_execution.py` | 134 | P2 Phase 6 — Execution Workflow tests. |
| `tests/test_p2_phase7_daily.py` | 96 | P2 Phase 7 — Daily Rhythm Workflow tests. |
| `tests/test_p2_phase8_integration.py` | 282 | P2 Phase 8 — Integration tests for all workflow domains. |
| `tests/test_p3_phase1_github.py` | 178 | P3 Phase 1 — GitHub Workflow tests. |
| `tests/test_p3_phase2_document.py` | 268 | P3 Phase 2 — Document Generation Workflow tests. |
| `tests/test_p3_phase3_browser.py` | 246 | P3 Phase 3 — Browser Task Workflow tests. |
| `tests/test_p3_phase4_slack.py` | 266 | P3 Phase 4 — Slack Workflow tests. |
| `tests/test_p3_phase5_design.py` | 241 | P3 Phase 5 — Design Workflow tests. |
| `tests/test_p4_sync_campaign_artifacts.py` | 130 | P4-SYNC campaign artifact validation — tenant safety + schema integrity. |
| `tests/test_p4s10_lyfeos_creatoros_readiness.py` | 150 | P4S-10 — LifeOS + CreatorOS projection read-surface accessors. |
| `tests/test_p4s11_capability_manifest.py` | 81 | P4S-11 — capability registry manifest tests. |
| `tests/test_p4s12_template_registry.py` | 356 | P4S-12 — RealityTemplate registry: metamodel + registry enforcement. |
| `tests/test_p4s20_eos_tasks_read.py` | 295 | P4S-20 — EOS `/eos/tasks` read surface tests (governed-effect visibility). |
| `tests/test_p4s31_intent_loop.py` | 308 | P4S-31 — UMH MVP intent→proof operating-loop skeleton tests. |
| `tests/test_p4s31b_intent_input_surface.py` | 420 | P4S-31B — Cockpit Chat intent rail (governed submit + decide). |
| `tests/test_p4s31c_read_path_hardening.py` | 254 | P4S-31C — read-path isolation + bounded snapshot regression tests. |
| `tests/test_p4s31d1_voice_ptt.py` | 416 | P4S-31D-1 — Desktop browser push-to-talk voice adapter into Cockpit Chat. |
| `tests/test_p4s31d1b_audio_storage.py` | 348 | P4S-31D1-B lane F — audio artifact storage law tests. |
| `tests/test_p4s31d1b_contract_artifacts.py` | 132 | P4S-31D1-B — VoiceMessage contract artifact validation (Lane B). |
| `tests/test_p4s31d1b_voice_message.py` | 349 | P4S-31D1-B — Cockpit voice-MESSAGE rail (lanes C+D+E). |
| `tests/test_p4s31d1c_capture_signal.py` | 122 | P4S-31D1-C — voice capture signal contract (root-cause fix + client diagnostics). |
| `tests/test_p4s31d1c_ui_signal.py` | 323 | P4S-31D1-C — voice-note UI capture-signal checks (live meter + precise failures). |
| `tests/test_p4s31d1e_artifact_binding.py` | 430 | P4S-31D1-E — the local MediaRecorder blob is the SINGLE SOURCE OF TRUTH. |
| `tests/test_p4s31d1e_binding_contract.py` | 114 | P4S-31D1-E — VoiceNote artifact-binding contract shape checks. |
| `tests/test_p4s31d1e_consent_flow.py` | 357 | P4S-31D1-E — single-gesture mobile-Safari consent flow. |
| `tests/test_p4s31d1e_transcript_ui.py` | 238 | P4S-31D1-E — collapsible transcript dropdown on the voice-note card. |
| `tests/test_p4s31d3_desktop_scaffold.py` | 189 | P4S-31D-3 SCAFFOLD — desktop app (Electron) voice adapter shell. |
| `tests/test_p4s31d_ambient_compile_artifacts.py` | 391 | P4S-31D desktop ambient wake-word compile-artifact validation — compile-mode gate. |
| `tests/test_p4s31d_mobile_compile_artifacts.py` | 346 | P4S-31D-4/5 mobile voice compile artifact validation — compile-mode gate. |
| `tests/test_p4s31d_voice_matrix_artifacts.py` | 280 | P4S-31D voice capability-matrix artifact validation — compile-mode gate. |
| `tests/test_permission_tiers.py` | 164 | Tests for the 4-tier permission model (Read/Draft/Execute/Commit). |
| `tests/test_persist_all_observations.py` | 223 | Tests for persist-all-observations — every observation becomes a memory entry. |
| `tests/test_persistent_loops.py` | 345 | Tests for the persistent loop infrastructure. |
| `tests/test_phase10_2_sandbox_pr.py` | 476 | Phase 10.2 — Operator-Approved Template-Supplied Sandbox PR Creation tests. |
| `tests/test_phase10_3_production_truth.py` | 272 | Phase 10.3 — Production truth promotion tests. |
| `tests/test_phase10_4_reliability_campaign.py` | 527 | Phase 10.4 — Low-risk production truth reliability campaign tests. |
| `tests/test_phase10_5_reliability_weighted_cadence.py` | 712 | Phase 10.5 — Reliability-Weighted Cadence Ranking + Promotion Thresholds. |
| `tests/test_phase13_3_context_assimilation.py` | 1,142 | Phase 13.3 — Context Assimilation + Continuous Reconciliation Kernel tests. |
| `tests/test_phase13_3s_operational_truth.py` | 701 | Phase 13.3S — Operational Truth Stabilization tests. |
| `tests/test_phase13_4_operator_e2e_acceptance.py` | 655 | Phase 13.4 — Standard Multi-Runtime Operator E2E Acceptance Tests. |
| `tests/test_phase14_11a_execution_control.py` | 191 | Phase 14.11A — execution control adapter tests. |
| `tests/test_phase14_11a_paused_lifecycle.py` | 89 | Phase 14.11A — PAUSED lifecycle state transition tests. |
| `tests/test_phase14_11a_workstation_endpoints.py` | 107 | Phase 14.11A — workstation endpoint and mode resolver tests. |
| `tests/test_phase14_11b_checkpoint_resume.py` | 245 | Phase 14.11B — Checkpoint + resume brief tests. |
| `tests/test_phase14_11b_continuity.py` | 209 | Phase 14.11B — Continuity state machine tests. |
| `tests/test_phase14_11b_dual_modes.py` | 193 | Phase 14.11B — Dual mode taxonomy + resolver tests. |
| `tests/test_phase14_11b_mode_switch_overnight.py` | 237 | Phase 14.11B — Mode switching + overnight scaffold tests. |
| `tests/test_phase14_11c_file_browser.py` | 218 | Phase 14.11C — File browser safety + functionality tests. |
| `tests/test_phase14_11c_workspace_endpoints.py` | 258 | Phase 14.11C — Workspace endpoint tests. |
| `tests/test_phase14_11d_activation_signal.py` | 210 | Phase 14.11D — ActivationSignal model tests. |
| `tests/test_phase14_11d_jarvis_command.py` | 307 | Phase 14.11D — Jarvis command routing + governance tests. |
| `tests/test_phase14_11d_presence_endpoints.py` | 206 | Phase 14.11D — Presence endpoint tests. |
| `tests/test_phase14_11d_voice_integration.py` | 258 | Phase 14.11D — Voice/STT/TTS integration and trace tests. |
| `tests/test_phase14_11e_agent_registry.py` | 244 | Phase 14.11E — Agent registry and command center route tests. |
| `tests/test_phase14_11e_jarvis_commands.py` | 199 | Phase 14.11E — Jarvis command integration tests for agent/task/work-packet commands. |
| `tests/test_phase14_11g_actionability.py` | 278 | Phase 14.11G — Integrated workstation actionability tests. |
| `tests/test_phase14_15_continuity.py` | 613 | Phase 14.15 — Full Continuity Daily Driver tests. |
| `tests/test_phase14_3_product_docs_convergence.py` | 556 | Phase 14.3 — Google Docs Product Documentation Convergence tests. |
| `tests/test_phase14_3a_full_content_convergence.py` | 597 | Phase 14.3A — Full Google Docs Product Documentation Convergence tests. |
| `tests/test_phase14_4_trinity_alignment.py` | 660 | Phase 14.4 — Trinity GitHub/Windows Alignment + Product Design Diff |
| `tests/test_phase14_5_convergence_planning.py` | 713 | Phase 14.5 — Trinity Convergence Planning / Decision Session |
| `tests/test_phase14_5a.py` | 897 | Phase 14.5A tests — 13-layer production stack + Socratic governance completion. |
| `tests/test_phase14_5r_production_truth.py` | 497 | Phase 14.5R — Trinity Convergence + 13-Layer + Socratic Governance Production Truth Promotion tests. |
| `tests/test_phase14_6b_creatoros_lossless_canon.py` | 1,294 | Comprehensive pytest test suite for CreatorOS Phase 14.6B canon reconstruction. |
| `tests/test_phase14_6b_eos_lossless_canon.py` | 1,398 | Comprehensive pytest test suite for EOS Phase 14.6B canon reconstruction. |
| `tests/test_phase14_6b_lyfeos_code_resolved_canon.py` | 1,652 | Phase 14.6B-LyfeOS: Code-Resolved Lossless LyfeOS Product Canon Reconstruction |
| `tests/test_phase14_6b_umh_code_resolved_canon.py` | 1,816 | Phase 14.6B-UMH: Code-Resolved Universal Meta Harness Canon Reconstruction |
| `tests/test_phase14_6c_operator_review.py` | 1,240 | Comprehensive pytest test suite for Phase 14.6C operator review packet. |
| `tests/test_phase14_6d_canon_revision.py` | 811 | Comprehensive pytest test suite for Phase 14.6D canon revision. |
| `tests/test_phase14_6e_p0_ratification.py` | 546 | Comprehensive pytest test suite for Phase 14.6E P0 ratification sprint. |
| `tests/test_phase14_6f_canon_revision.py` | 859 | Comprehensive pytest test suite for Phase 14.6F cross-product canon revision sprint. |
| `tests/test_phase14_6g_readiness_gate.py` | 580 | Phase 14.6G: UMH Stage 1 Functional Organism Readiness Gate Tests |
| `tests/test_phase14_7a_wave1.py` | 738 | Phase 14.7A Wave 1 — Foundation Wiring tests. |
| `tests/test_phase14_7a_wave2.py` | 453 | Phase 14.7A Wave 2 — Organism Loop tests. |
| `tests/test_phase14_7a_wave3.py` | 379 | Phase 14.7A Wave 3 — Self-Improvement Loop tests. |
| `tests/test_phase14_7b_cockpit_usability.py` | 575 | Phase 14.7B — Cockpit Command Surface Wiring + Internal Operator Usability. |
| `tests/test_phase14_8a_wp12.py` | 294 | Phase 14.8A WP-1.2 — WorldModelPanel wiring to reality model routes. |
| `tests/test_phase14_8b_wave2.py` | 373 | Phase 14.8B Wave 2 — Organism Loop wiring tests. |
| `tests/test_phase14_8c_wave3.py` | 605 | Phase 14.8C Wave 3 tests — outcome recording, cadence enforcement, |
| `tests/test_phase17_organism_loop_e2e.py` | 316 | Phase 17 — Organism Loop E2E integration tests. |
| `tests/test_phase18_operator_convergence.py` | 412 | Phase 18 — Operator Convergence integration tests. |
| `tests/test_phase19_reality_canonicalization.py` | 502 | Phase 19 — Reality Canonicalization E2E tests. |
| `tests/test_phase20_reality_intelligence.py` | 655 | Phase 20 — Reality Intelligence tests. |
| `tests/test_phase21_meta_ide_convergence.py` | 507 | Tests for Phase 21 — Meta IDE Convergence. |
| `tests/test_phase22_autonomous_engineering.py` | 772 | Phase 22 — Autonomous Engineering Loop tests. |
| `tests/test_phase23_engineering_proof_loop.py` | 840 | Phase 23 — Engineering Proof Loop test suite. |
| `tests/test_phase24_distributed_worker_runtime.py` | 811 | Phase 24 — Distributed Worker Runtime test suite. |
| `tests/test_phase25_workspace_observation.py` | 893 | Phase 25 — Workspace Observation tests. |
| `tests/test_phase26_action_bridge.py` | 785 | Phase 26 — Governed Action Bridge tests. |
| `tests/test_phase27_workspace_runtime_graph.py` | 704 | Tests for Phase 27 — Workspace Runtime Graph. |
| `tests/test_phase28_umh_node_role_version_topology.py` | 758 | Phase 28 — UMH Node Role & Version Topology tests. |
| `tests/test_phase29_state_authority_graph.py` | 801 | Phase 29 — Organism State Authority & Coherence tests. |
| `tests/test_phase30_service_dependency_graph.py` | 980 | Phase 30 — Service Dependency & Failure Graph tests. |
| `tests/test_phase31_operator_home.py` | 1,016 | Phase 31 — Operator Home & Context Engine tests. |
| `tests/test_phase32_presence_continuity.py` | 1,281 | Phase 32 — Presence & Continuity Runtime tests. |
| `tests/test_phase33_screen_awareness.py` | 1,396 | Phase 33 — Screen Awareness Runtime tests. |
| `tests/test_phase34_workstation_observation.py` | 1,171 | Phase 34 — Workstation Observation Runtime tests. |
| `tests/test_phase35_voice_runtime.py` | 1,049 | Phase 35 — Voice Query Engine tests. |
| `tests/test_phase9_5_spine_native_propagation.py` | 853 | Phase 9.5 — Spine-Native Propagation + Template-Guided Campaign Tests. |
| `tests/test_phase9_5b_template_campaign.py` | 437 | Phase 9.5B — Real Template-Guided Improvement Campaign Tests. |
| `tests/test_phase9_6_autonomous_lane.py` | 1,001 | Phase 9.6 — Autonomous Improvement Lane Tests. |
| `tests/test_phase9_7_pr_factory.py` | 1,103 | Phase 9.7 — Sandboxed Autonomous PR Factory tests. |
| `tests/test_phase9_8_production_truth.py` | 1,859 | Phase 9.8 — Production Truth Promotion + Scheduled Autonomous Cadence tests. |
| `tests/test_philosophy_lenses.py` | 153 | Tests for substrate.understanding.knowledge.philosophy_lenses. |
| `tests/test_prediction_portfolio_runtime.py` | 313 | Tests for PredictionPortfolioRuntime — Campaign 13.2. |
| `tests/test_prediction_routes.py` | 96 | Tests for cockpit prediction routes — Campaign 13.3. |
| `tests/test_presence_runtime.py` | 797 | Tests for Phase 8: Presence Runtime. |
| `tests/test_priority_engine.py` | 305 | Campaign 7.1 — Priority Engine tests. |
| `tests/test_product_connections.py` | 129 | Tests for substrate.integrations.product_connections. |
| `tests/test_profile_runtime.py` | 969 | Tests for Phase 11 — Profile Runtime. |
| `tests/test_project_registry.py` | 303 | Tests for Project Registry — Campaign 5.2. |
| `tests/test_projection_certification.py` | 447 | Tests for C26C — Projection Certification Framework. |
| `tests/test_projection_delta.py` | 206 | Tests for projection delta engine. |
| `tests/test_projection_drift_reconciliation.py` | 173 | Projection drift reconciliation — WP-P4-SOURCE-RECONCILIATION-001. |
| `tests/test_projection_engine.py` | 771 | Tests for Phase 6: Projection Engine. |
| `tests/test_projection_integration_runtime.py` | 346 | Tests for ProjectionIntegrationRuntime — Campaign 3.5. |
| `tests/test_projection_port_convergence.py` | 198 | WP-P3-004 — projection registration/port convergence tests. |
| `tests/test_projection_read_surface_discipline.py` | 181 | Projection read-surface discipline — P4-SURFACE-DISCIPLINE. |
| `tests/test_projection_registry_read_convergence.py` | 216 | WP-P3 — read-side projection registry consumer convergence tests. |
| `tests/test_projection_source_sync.py` | 128 | WP-P4-BEAST-SOURCE-SYNC-001 — guards for the Beast projection source-readiness harness. |
| `tests/test_projection_source_truth.py` | 117 | Projection Source-Truth Law — governance test (P4-PROJECTION-SOURCE-TRUTH). |
| `tests/test_provider_state.py` | 208 | Tests for runtime.provider_state — global failure state + backpressure. |
| `tests/test_reality_ambush.py` | 532 | Reality Ambush Test — Phase 1 Final Gate. |
| `tests/test_reality_benchmark.py` | 135 | Tests for C26F Reality Correspondence Benchmark. |
| `tests/test_reality_graph.py` | 545 | Tests for Reality Graph — Campaign 5.0. |
| `tests/test_reality_model.py` | 94 | — |
| `tests/test_recommendation_engine.py` | 309 | Campaign 7.3 — Recommendation Engine tests. |
| `tests/test_registry.py` | 104 | Tests for ConcreteComponentRegistry. |
| `tests/test_registry_truthfulness.py` | 91 | WP-P2-001 — negative-control tests for the registry truthfulness audit. |
| `tests/test_repository_awareness.py` | 354 | Tests for Campaign 6.1 — Repository Awareness Runtime. |
| `tests/test_resource_allocation_runtime.py` | 349 | Tests for ResourceAllocationRuntime — Campaign 14.0. |
| `tests/test_risk_engine.py` | 253 | Campaign 7.2 — Risk Engine tests. |
| `tests/test_risk_taxonomy_canonical.py` | 156 | WP-P2-002 — canonical risk vocabulary + fail-closed coercion tests. |
| `tests/test_runtime_awareness.py` | 315 | Tests for Campaign 6.3 — Runtime Awareness Runtime. |
| `tests/test_runtime_state_registry.py` | 433 | Tests for Runtime State Registry — Phase 16. |
| `tests/test_scenario_intelligence_engine.py` | 297 | Tests for ScenarioIntelligenceEngine — Campaign 13.1. |
| `tests/test_secrets_runtime_protocol.py` | 179 | WP-P4-SECRETS-RUNTIME-001 — guards for the UMH 1Password Secret Runtime Protocol. |
| `tests/test_self_model.py` | 349 | Tests for substrate.self_model — the system's self-awareness foundation. |
| `tests/test_self_use_catalog.py` | 147 | Tests for C27 self-use task catalog. |
| `tests/test_self_use_gap_ledger.py` | 135 | Tests for C27 gap ledger. |
| `tests/test_self_use_report.py` | 182 | Tests for C27 certification report. |
| `tests/test_session_machine_runtime.py` | 343 | Tests for SessionMachineRuntime — Campaign 19.2. |
| `tests/test_session_runtime.py` | 1,012 | Tests for Phase 12: Session Runtime. |
| `tests/test_single_spine_architecture.py` | 173 | WP-P1-001 architecture test — one canonical governed operation runtime. |
| `tests/test_source_truth_linker.py` | 412 | Tests for Source Truth Linker — Campaign 5.4. |
| `tests/test_spine_full.py` | 174 | Tests for ConcreteExecutionSpine — the LLM/cognitive 8-stage pipeline. |
| `tests/test_sprint1_smoke.py` | 264 | Sprint 1 smoke tests — production stabilization. |
| `tests/test_sprint2_boundary.py` | 121 | Sprint 2 boundary repair tests — verify substrate→adapters type extraction. |
| `tests/test_sprint3_recovery.py` | 73 | Sprint 3 — Test Recovery verification. |
| `tests/test_sprint4_data_hygiene.py` | 116 | Sprint 4 — Data/Log Hygiene verification. |
| `tests/test_sprint5_doc_truth.py` | 80 | Sprint 5 — Documentation Truth verification. |
| `tests/test_stage1_acceptance_e2e.py` | 721 | Phase 14.9A — Stage 1 E2E Acceptance Validation. |
| `tests/test_strategic_context_runtime.py` | 397 | Campaign 7.0 — Strategic Context Runtime tests. |
| `tests/test_strategic_gap_engine.py` | 667 | Strategic Gap Engine — Phase 4 acceptance tests. |
| `tests/test_strategic_memory_engine.py` | 550 | Tests for Campaign 9.4 — Strategic Memory Engine. |
| `tests/test_strategic_planning_engine.py` | 392 | Tests for StrategicPlanningEngine — Campaign 8.3. |
| `tests/test_strategic_tick_loop.py` | 664 | Tests for Phase 5: Strategic Tick Loop. |
| `tests/test_tme_active_tool_context.py` | 188 | Tests for the TME Active Tool Context. |
| `tests/test_tme_mastery_assurance_gate.py` | 256 | Tests for the TME Mastery Assurance Gate. |
| `tests/test_tme_natural_language_resolver.py` | 204 | Tests for the TME Natural Language Tool Mastery Resolver. |
| `tests/test_trace_recorder.py` | 89 | Tests for ConcreteTraceRecorder. |
| `tests/test_tradeoff_intelligence_engine.py` | 289 | Tests for TradeoffIntelligenceEngine — Campaign 14.1. |
| `tests/test_trajectory_intelligence_runtime.py` | 348 | Tests for TrajectoryIntelligenceRuntime — Campaign 13.0. |
| `tests/test_transformation_state_ledger.py` | 430 | Tests for Transformation State Ledger -- Phase 96.8V. |
| `tests/test_transport_app_import.py` | 59 | WP-P4-004 — transport app import viability. |
| `tests/test_trust_score.py` | 264 | Tests for TrustScoreEngine — C26E Phase 2. |
| `tests/test_type_divergence.py` | 157 | Tests for the type divergence detection system. |
| `tests/test_unified_approval_authority.py` | 227 | WP-P1-007 — unified approval authority behavior tests. |
| `tests/test_unified_approval_runtime.py` | 542 | Tests for UnifiedApprovalRuntime — Campaign 4.2. |
| `tests/test_unified_execution_surface_runtime.py` | 602 | Tests for UnifiedExecutionSurfaceRuntime — Campaign 3.3. |
| `tests/test_unified_workstation_runtime.py` | 322 | Tests for UnifiedWorkstationRuntime — Campaign 18.0. |
| `tests/test_vision.py` | 239 | Tests for Phase 14.14B — DEX Vision Embodiment. |
| `tests/test_vision_14_16.py` | 665 | Tests for Phase 14.16 — Realtime Vision Overlay + Tracker Stack + Vision Preset Studio + Trigger Chain Engine. |
| `tests/test_vision_14_17.py` | 354 | Tests for Phase 14.17 — Vision Reliability Hardening. |
| `tests/test_vision_14_18.py` | 642 | Tests for Phase 14.18 — Camera Default-On + Realtime PTZ Control Loop + Smooth Vision UX. |
| `tests/test_vision_14_18c.py` | 340 | Tests for Phase 14.18C/19B — True PTZ Joystick + Overlay Visibility + Diagnostics. |
| `tests/test_vision_14e.py` | 673 | Tests for Phase 14.14E — Voice Camera Control, Tracking, Scene Understanding. |
| `tests/test_voice_error_code_canonical.py` | 48 | P4S31 Voice Convergence — the ONE voice error taxonomy. |
| `tests/test_voice_error_codes_ts_mirror.py` | 48 | P4S31 Voice Convergence — the TS mirror matches the Python enum byte-for-byte. |
| `tests/test_voice_idempotency.py` | 176 | Phase 14.13V: Voice turn idempotency tests. |
| `tests/test_voice_identity.py` | 289 | Phase 14.13U: Voice identity and source sync tests. |
| `tests/test_voice_process_audio_blob.py` | 175 | P4S31 Voice Convergence — canonical VoiceSession runtime upgrades (Commit 2). |
| `tests/test_voice_rival_retired.py` | 82 | P4S31 Voice Convergence — the rival voice runtimes are RETIRED (Commit 4). |
| `tests/test_voice_route_resolver.py` | 256 | Tests for substrate/workstation/voice_route_resolver.py. |
| `tests/test_voice_runtime_divergence.py` | 78 | P4S31 Voice Convergence — Gate 14 regression tests. |
| `tests/test_voice_session_store.py` | 143 | P4S31 Voice Convergence — the ONE canonical voice record store. |
| `tests/test_voice_turn_assembly.py` | 264 | Phase 14.13V: Voice turn assembly tests. |
| `tests/test_voice_ws_endpoint.py` | 310 | P4S31 Voice Convergence — the governed voice WS endpoint (Commit 3). |
| `tests/test_work_intelligence_routes.py` | 310 | Tests for cockpit work intelligence routes — Campaign 11.3. |
| `tests/test_work_lanes.py` | 548 | Tests for Beast multi-session work lanes, app resolver, and loop engine. |
| `tests/test_work_portfolio_runtime.py` | 512 | Tests for WorkPortfolioRuntime — Campaign 11.2. |
| `tests/test_work_readiness_runtime.py` | 343 | Tests for WorkReadinessRuntime — Campaign 11.0. |
| `tests/test_work_state.py` | 171 | Tests for runtime.work_state — idle detection + adaptive throttling. |
| `tests/test_workspace_awareness.py` | 419 | Tests for Workspace Awareness Runtime — Campaign 5.1. |
| `tests/test_workstation_executor.py` | 1,101 | Tests for WorkstationExecutor — Phase 15A. |
| `tests/test_workstation_mvp_loop.py` | 366 | Integration tests for Campaign 17 — Workstation MVP Loop. |
| `tests/test_workstation_presence_runtime.py` | 212 | Tests for Campaign 17.2 — WorkstationPresenceRuntime. |
| `tests/test_workstation_runtime.py` | 896 | Tests for Phase 10 — Workstation Runtime. |
| `tests/test_workstation_session_runtime.py` | 461 | Tests for WorkstationSessionRuntime — Campaign 4.4. |

## tests/adapters/ (5 files)

| Path | Lines | Purpose |
|---|---|---|
| `tests/adapters/__init__.py` | 0 | package marker (empty) |
| `tests/adapters/broadcast/__init__.py` | 0 | package marker (empty) |
| `tests/adapters/broadcast/test_filtergraph.py` | 252 | Unit tests for multi-source filtergraph builder + scene switch commands. |
| `tests/adapters/broadcast/test_node_dispatch.py` | 200 | Unit tests for Phase 0 — organism engine placement. |
| `tests/adapters/broadcast/test_process_lifecycle.py` | 142 | Tests for ProcessLifecycle fixes: stale exit, SIGKILL timeout, lock, cancel race. |

## tests/certification/ (7 files)

| Path | Lines | Purpose |
|---|---|---|
| `tests/certification/__init__.py` | 0 | package marker (empty) |
| `tests/certification/c28_certification.py` | 582 | C28 Certification Suite — Cockpit Supremacy / Meta IDE Daily Driver. |
| `tests/certification/c28_panel_audit.py` | 267 | C28 Panel Audit — runs ON Beast with real Playwright display. |
| `tests/certification/c28_task_acceptance.py` | 484 | C28 10-Task Acceptance Test — runs ON Beast with real Playwright display. |
| `tests/certification/c29_benchmark.py` | 1,445 | C29 Harness Superiority Benchmark — CLI Runner. |
| `tests/certification/c29_evidence.py` | 1,015 | C29 Harness Superiority — Browser Evidence Collector. |
| `tests/certification/c29_report.py` | 901 | C29 Harness Superiority — Certification Report Generator. |

## tests/fixtures/ (6 files)

| Path | Lines | Purpose |
|---|---|---|
| `tests/fixtures/ingestion_fixture.md` | 39 | UMH Architecture and Runtime Procedures — XQVR7-ZEPHYR-CANARY-9F3K |
| `tests/fixtures/voice/generate_fixtures.py` | 180 | Generate SMALL synthetic voice fixtures for the P4S-31D1-C STT pipeline tests. |
| `tests/fixtures/voice/ios_audio_mp4.marker.json` | 18 | — |
| `tests/fixtures/voice/known_good_tone.wav` | — | wav asset (19,244 B) |
| `tests/fixtures/voice/mid_sentence_pause.wav` | — | wav asset (64,044 B) |
| `tests/fixtures/voice/silence.wav` | — | wav asset (25,644 B) |

## tests/substrate/ (4 files)

| Path | Lines | Purpose |
|---|---|---|
| `tests/substrate/__init__.py` | 0 | package marker (empty) |
| `tests/substrate/test_entity_store.py` | 319 | Tests for substrate.state.stores.entity_store — entity persistence layer. |
| `tests/substrate/test_feedback_loop.py` | 386 | Tests for substrate.execution.feedback_loop — RLHF feedback ingestion + learning cycle. |
| `tests/substrate/test_types.py` | 208 | — |
