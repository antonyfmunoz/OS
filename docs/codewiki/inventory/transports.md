---
type: codewiki-inventory
dir: transports
source_sha: 70deadbac8667755a38ac49595afd09afc209c2f
---

# `transports/` — File Inventory

**Files:** 221 regular + 0 symlinks · **Bytes:** 2,047,311

[Narrative page](../dirs/transports.md)


## transports/ (root)

| Path | Lines | Purpose |
|---|---|---|
| `transports/__init__.py` | 0 | package marker (empty) |

## transports/api/ (169 files)

| Path | Lines | Purpose |
|---|---|---|
| `transports/api/__init__.py` | 0 | package marker (empty) |
| `transports/api/_mesh_dispatch.py` | 316 | Mesh dispatch — sends engineering plan tasks to a connected node via mesh HTTP relay. |
| `transports/api/agent_bridge.py` | 138 | Stdin/stdout JSON bridge between the TypeScript API and the Python AI layer. |
| `transports/api/agent_routes.py` | 160 | Agent Executor API routes — governed cognitive worker endpoints. |
| `transports/api/app.py` | 723 | UMH API server — FastAPI surface matching existing UMH service conventions. |
| `transports/api/approval_routes.py` | 160 | Approval Intercept route handlers. |
| `transports/api/cockpit.py` | 1,571 | Cockpit API endpoints — serves real data from UMH stores to the frontend. |
| `transports/api/cockpit_action_bridge_routes.py` | 146 | Cockpit routes for the Governed Action Bridge (Phase 26). |
| `transports/api/cockpit_activity_routes.py` | 229 | Cockpit Activity Routes — canonical activity/timeline capability surface. |
| `transports/api/cockpit_adapter_status_routes.py` | 69 | Cockpit adapter status routes — read-only observability for the adapter fleet. |
| `transports/api/cockpit_agent_fleet_routes.py` | 201 | Cockpit agent fleet routes — unified agent coordination surface. |
| `transports/api/cockpit_agent_workforce_routes.py` | 70 | Cockpit routes for AgentWorkforceRuntime — Campaign 19.1. |
| `transports/api/cockpit_ambient_wake_routes.py` | 65 | Cockpit routes for AmbientWakeRuntime — Campaign 20.2. |
| `transports/api/cockpit_artifact_registry_routes.py` | 63 | Cockpit routes for Artifact Registry — Campaign 6.0. |
| `transports/api/cockpit_attention_routes.py` | 42 | Cockpit routes for AttentionAggregationRuntime — Campaign 18.2. |
| `transports/api/cockpit_audit.py` | 107 | Cockpit audit event emitter — settings + unified mutation audit trail. |
| `transports/api/cockpit_auth.py` | 222 | Clerk JWT server-side validation for cockpit API. |
| `transports/api/cockpit_autonomous_routes.py` | 616 | Cockpit autonomous PR factory and cadence scheduler routes. |
| `transports/api/cockpit_broadcast_routes.py` | 625 | Broadcast API — start/stop/status + WebSocket health push. |
| `transports/api/cockpit_capability_intelligence_routes.py` | 181 | Cockpit routes for Capability Intelligence — Campaign 10.4. |
| `transports/api/cockpit_capability_map_routes.py` | 70 | Cockpit Capability Map Routes — API surface for cockpit audit. |
| `transports/api/cockpit_capability_routes.py` | 190 | Cockpit Capability Routes — API surface for emergent capability tracking. |
| `transports/api/cockpit_chat_routes.py` | 837 | Cockpit chat routes — advisor/dex conversation + operator chat. |
| `transports/api/cockpit_command_center_mvp_routes.py` | 126 | Command Center MVP Routes — operator landing surface API. |
| `transports/api/cockpit_command_center_routes.py` | 815 | Cockpit command center routes — agent registry, work packet board, summary. |
| `transports/api/cockpit_compounding_routes.py` | 178 | Cockpit Compounding Routes — API surface for capability compounding. |
| `transports/api/cockpit_compute_fabric_routes.py` | 105 | Cockpit compute fabric routes — unified compute body map surface. |
| `transports/api/cockpit_context_assimilation_routes.py` | 641 | Cockpit context assimilation routes — source registry, ingestion, |
| `transports/api/cockpit_context_resolution_routes.py` | 75 | Cockpit routes for Context Resolution — Campaign 5.5. |
| `transports/api/cockpit_core_bootstrap_routes.py` | 487 | Cockpit bootstrap routes — extracted from cockpit_core_routes.py. |
| `transports/api/cockpit_core_creatoros_routes.py` | 33 | Cockpit CreatorOS projection routes — P4S-10. |
| `transports/api/cockpit_core_eos_routes.py` | 287 | Cockpit EOS projection routes — extracted from cockpit_core_routes.py. |
| `transports/api/cockpit_core_feedback_routes.py` | 155 | Cockpit feedback & notification routes — extracted from cockpit_core_routes.py. |
| `transports/api/cockpit_core_governance_routes.py` | 195 | Cockpit governance routes — extracted from cockpit_core_routes.py. |
| `transports/api/cockpit_core_lyfeos_routes.py` | 32 | Cockpit LyfeOS projection routes — P4S-10. |
| `transports/api/cockpit_core_routes.py` | 2,127 | Cockpit core routes — extracted inline route handlers. |
| `transports/api/cockpit_core_session_routes.py` | 302 | Cockpit session & device routes — extracted from cockpit_core_routes.py. |
| `transports/api/cockpit_delegation_routes.py` | 196 | Cockpit routes for Delegation Runtime — Campaign 4.7. |
| `transports/api/cockpit_device_routes.py` | 487 | Cockpit device management routes — scan, diagnose, register, provision. |
| `transports/api/cockpit_distributed_runtime_routes.py` | 251 | Cockpit distributed runtime routes — organism worker routing surface. |
| `transports/api/cockpit_documentation_awareness_routes.py` | 66 | Cockpit routes for Documentation Awareness — Campaign 6.2. |
| `transports/api/cockpit_economy_routes.py` | 465 | Cockpit organism economy, recursion, advisor hierarchy, assimilation, snapshot, |
| `transports/api/cockpit_embodiment_routes.py` | 154 | Cockpit Embodiment routes — natural language intent surface. |
| `transports/api/cockpit_engineering_review_routes.py` | 334 | Cockpit engineering review routes — execution sessions and proof review. |
| `transports/api/cockpit_engineering_routes.py` | 320 | Cockpit engineering routes — autonomous planning and packetization. |
| `transports/api/cockpit_entity_routes.py` | 362 | Cockpit entity and product routes — portfolio, departments, roles, companies |
| `transports/api/cockpit_execution_fabric_routes.py` | 70 | Cockpit routes for ExecutionFabricRuntime — Campaign 19.0. |
| `transports/api/cockpit_execution_graph_routes.py` | 148 | Cockpit Execution Graph Routes — API surface for lineage validation. |
| `transports/api/cockpit_execution_loop_routes.py` | 589 | Cockpit execution and loop routes — persistent loops + execution substrate. |
| `transports/api/cockpit_execution_routes.py` | 300 | Cockpit Execution Routes — canonical execution capability surface. |
| `transports/api/cockpit_executive_routes.py` | 143 | Cockpit routes for Executive Intelligence — Campaign 14.3. |
| `transports/api/cockpit_goal_routes.py` | 191 | Cockpit routes for Goal Systems & Strategic Planning — Campaign 8.6. |
| `transports/api/cockpit_governance_routes.py` | 145 | Cockpit routes for Organism Governance — Campaign 15.4. |
| `transports/api/cockpit_infrastructure_routes.py` | 182 | Cockpit Infrastructure Routes — API surface for infrastructure registry. |
| `transports/api/cockpit_intent_loop_routes.py` | 262 | Cockpit intent-loop routes — P4S-31 read surface + P4S-31B intent rail seams. |
| `transports/api/cockpit_intent_routes.py` | 247 | Cockpit Intent Routes — API surface for intent preservation runtime. |
| `transports/api/cockpit_knowledge_awareness_routes.py` | 60 | Cockpit routes for Knowledge Awareness — Campaign 6.4. |
| `transports/api/cockpit_learning_routes.py` | 207 | Cockpit routes for Learning Intelligence — Campaign 12.4. |
| `transports/api/cockpit_loop_coherence_routes.py` | 91 | Cockpit routes for Operating Loop Coherence Runtime — Campaign 4.3. |
| `transports/api/cockpit_memory_routes.py` | 308 | Cockpit routes for Decision Intelligence & Strategic Memory — Campaign 9.6. |
| `transports/api/cockpit_meta_ide_context_routes.py` | 83 | Cockpit routes for Meta IDE Context — Campaign 17.1. |
| `transports/api/cockpit_meta_ide_conv_routes.py` | 238 | Cockpit Meta IDE convergence routes — unified development surface. |
| `transports/api/cockpit_meta_ide_critical_routes.py` | 407 | Meta IDE critical path routes — planning, work packets, proof packages, trust. |
| `transports/api/cockpit_meta_ide_projection_loop_routes.py` | 166 | Cockpit Meta IDE Projection Loop Routes — API surface for build loop. |
| `transports/api/cockpit_meta_ide_routes.py` | 260 | Cockpit Meta IDE routes — engineering reality awareness. |
| `transports/api/cockpit_migration_routes.py` | 182 | Cockpit Operator Migration routes — exit tracking and closure. |
| `transports/api/cockpit_mvp_readiness_routes.py` | 64 | Cockpit routes for MVP Readiness Runtime — Campaign 4.5. |
| `transports/api/cockpit_operating_loop_routes.py` | 115 | Cockpit routes for Operating Loop Runtime — Campaign 4.1. |
| `transports/api/cockpit_operationalization_routes.py` | 166 | Cockpit Operationalization Routes — API surface for reusable capability artifacts. |
| `transports/api/cockpit_operator_experience_routes.py` | 203 | Cockpit operator experience routes — session, send, preview, status. |
| `transports/api/cockpit_operator_home_routes.py` | 106 | Cockpit Operator Home Routes — unified operator context API. |
| `transports/api/cockpit_operator_loop_ext_routes.py` | 1,148 | Cockpit operator loop extension routes — Phases 5-8. |
| `transports/api/cockpit_operator_loop_routes.py` | 1,574 | Cockpit operator loop routes — intent to plan to implementation to audit. |
| `transports/api/cockpit_operator_loop_session_routes.py` | 897 | Cockpit operator loop session routes — Phases 9-12. |
| `transports/api/cockpit_operator_presence_routes.py` | 102 | Cockpit Operator Presence Routes — presence and continuity API. |
| `transports/api/cockpit_operator_timeline_routes.py` | 159 | Cockpit operator timeline routes — unified chronological activity view. |
| `transports/api/cockpit_orchestrator_awareness_routes.py` | 69 | Cockpit routes for Orchestrator Awareness Runtime — Campaign 4.0. |
| `transports/api/cockpit_orchestrator_presence_routes.py` | 80 | Cockpit routes for Orchestrator Presence — Campaign 17.0. |
| `transports/api/cockpit_organism_map_routes.py` | 230 | Cockpit Organism Map Routes — unified topology for the organism map instrument. |
| `transports/api/cockpit_organism_routes.py` | 858 | Cockpit organism core routes — status, agents, deliverables, events, tick, |
| `transports/api/cockpit_prediction_routes.py` | 199 | Cockpit routes for Prediction Intelligence — Campaign 13.3. |
| `transports/api/cockpit_presence_routes.py` | 595 | Cockpit presence routes — activation, session, command, capabilities. |
| `transports/api/cockpit_production_routes.py` | 328 | Cockpit production routes — software production organism surface. |
| `transports/api/cockpit_projection_integration_routes.py` | 111 | Cockpit Projection Integration Routes — API surface for projection audit. |
| `transports/api/cockpit_projection_routes.py` | 106 | Cockpit routes for Gate 10 — Projection Consumption Layer. |
| `transports/api/cockpit_proof_inspector_routes.py` | 278 | Cockpit Proof Inspector routes — G10 MVP gate. |
| `transports/api/cockpit_propagation_graph_routes.py` | 245 | Cockpit propagation graph routes — graph, impact, plan, execute, results. |
| `transports/api/cockpit_push_routes.py` | 228 | Cockpit push notification routes — VAPID key exchange + subscription management. |
| `transports/api/cockpit_reality_graph_routes.py` | 103 | Cockpit routes for Reality Graph — Campaign 5.0. |
| `transports/api/cockpit_reality_intelligence_routes.py` | 220 | Cockpit reality intelligence routes — read-only reality retrieval. |
| `transports/api/cockpit_reality_model_routes.py` | 410 | Cockpit reality model routes — canonical patterns, instance observations, simulation. |
| `transports/api/cockpit_recovery_dashboard_routes.py` | 246 | Cockpit Recovery Dashboard routes — G11 MVP gate. |
| `transports/api/cockpit_repository_awareness_routes.py` | 69 | Cockpit routes for Repository Awareness — Campaign 6.1. |
| `transports/api/cockpit_rooms_routes.py` | 2,371 | Conference Rooms API — servers, categories, channels, messages, threads, forums, |
| `transports/api/cockpit_runtime_awareness_routes.py` | 59 | Cockpit routes for Runtime Awareness — Campaign 6.3. |
| `transports/api/cockpit_runtime_surface_routes.py` | 221 | Cockpit runtime surface routes — session lifecycle, events, adapters. |
| `transports/api/cockpit_screen_awareness_routes.py` | 145 | Cockpit Screen Awareness Routes — operator visual workspace context. |
| `transports/api/cockpit_self_build_routes.py` | 217 | Cockpit self-build queue routes — summary, items, next, blocked, ready, |
| `transports/api/cockpit_self_improvement_routes.py` | 486 | Cockpit self-improvement loop routes — outcome assimilation, verification, |
| `transports/api/cockpit_service_graph_routes.py` | 108 | Cockpit Service Graph Routes — read-only service dependency API. |
| `transports/api/cockpit_session_machine_routes.py` | 63 | Cockpit routes for SessionMachineRuntime — Campaign 19.2. |
| `transports/api/cockpit_session_routes.py` | 127 | Cockpit routes for Workstation Session Runtime — Campaign 4.4. |
| `transports/api/cockpit_settings_mutations.py` | 423 | Settings Mutation Runtime — single entry point for all settings mutations. |
| `transports/api/cockpit_spine_router.py` | 823 | Cockpit spine router — GovernedExecutionSpine, Journal, MutationRegistry, |
| `transports/api/cockpit_state_authority_routes.py` | 99 | Cockpit State Authority Routes — read-only state domain authority API. |
| `transports/api/cockpit_strategic_routes.py` | 187 | Cockpit routes for Strategic Context — Campaign 7.6. |
| `transports/api/cockpit_umh_node_routes.py` | 100 | Cockpit UMH Node Topology Routes — read-only node topology API. |
| `transports/api/cockpit_unified_approval_routes.py` | 274 | Cockpit routes for Unified Approval Runtime — Campaign 4.2. |
| `transports/api/cockpit_unified_execution_routes.py` | 146 | Unified Execution Surface Routes — single API surface across all execution subsystems. |
| `transports/api/cockpit_unified_workstation_routes.py` | 262 | Cockpit routes for UnifiedWorkstationRuntime — Campaign 18.0. |
| `transports/api/cockpit_universal_work_routes.py` | 298 | Cockpit universal work queue routes — packets, workcells, roles, knowledge. |
| `transports/api/cockpit_validation_routes.py` | 309 | Cockpit validation routes — capability compounding proof + competitive matrix surface. |
| `transports/api/cockpit_visual_attention_routes.py` | 50 | Cockpit routes for AttentionVisionRuntime — Campaign 21.3. |
| `transports/api/cockpit_visual_awareness_routes.py` | 64 | Cockpit routes for ScreenAwarenessRuntime — Campaign 21.0. |
| `transports/api/cockpit_visual_context_routes.py` | 57 | Cockpit routes for VisualContextRuntime — Campaign 21.2. |
| `transports/api/cockpit_visual_environment_routes.py` | 50 | Cockpit routes for EnvironmentAwarenessRuntime — Campaign 21.1. |
| `transports/api/cockpit_visual_ops_routes.py` | 78 | Cockpit routes for VisualOperationsRuntime — Campaign 21.4. |
| `transports/api/cockpit_voice_consent_routes.py` | 245 | Cockpit voice consent routes — P4S-31D-1 (VoiceConsentGrant surface). |
| `transports/api/cockpit_voice_ingress_routes.py` | 42 | Cockpit routes for VoiceIngressRuntime — Campaign 20.0. |
| `transports/api/cockpit_voice_ops_routes.py` | 71 | Cockpit routes for VoiceOperationsRuntime — Campaign 20.4. |
| `transports/api/cockpit_voice_output_routes.py` | 35 | Cockpit routes for VoiceOutputRuntime — Campaign 20.3. |
| `transports/api/cockpit_voice_routes.py` | 105 | Cockpit Voice Query Routes — context-grounded query resolution. |
| `transports/api/cockpit_voice_session_routes.py` | 91 | Cockpit routes for VoiceSessionManager — Campaign 20.1. |
| `transports/api/cockpit_work_center_routes.py` | 237 | Cockpit Work Center Routes — unified API for governed work lifecycle. |
| `transports/api/cockpit_work_intelligence_routes.py` | 199 | Cockpit routes for Work Intelligence — Campaign 11.3. |
| `transports/api/cockpit_workspace_observation_routes.py` | 122 | Cockpit workspace observation routes — live engineering runtime observation. |
| `transports/api/cockpit_workspace_routes.py` | 658 | Cockpit workspace routes — file browser, diff, test results, logs, proof, health. |
| `transports/api/cockpit_workspace_topology_routes.py` | 107 | Cockpit routes for Workspace Topology (Phase 27). |
| `transports/api/cockpit_workstation_control_routes.py` | 1,119 | Cockpit workstation control routes — execution pause/resume/stop with environment awareness. |
| `transports/api/cockpit_workstation_presence_routes.py` | 114 | Cockpit routes for Workstation Presence — Campaign 17.2. |
| `transports/api/computer_use.py` | 261 | Execution substrate API — governed multi-layer agent execution. |
| `transports/api/distribution.py` | 124 | Distribution API — channel status, intake, approval, and first-boot endpoints. |
| `transports/api/event_bus.py` | 72 | Event bus — pub/sub backbone for the substrate's internal communication. |
| `transports/api/execcoord_routes.py` | 224 | Phase 13: Execution Coordinator route handlers. |
| `transports/api/executor_routes.py` | 252 | Phase 14: Executor Runtime route handlers. |
| `transports/api/governed.py` | 111 | Governed mutation wrapper for FastAPI route handlers. |
| `transports/api/http/db/client.ts` | 91 | Database client for UMH API. |
| `transports/api/http/db/migrate.ts` | 167 | Migration runner. |
| `transports/api/http/db/schema.ts` | 221 | API/WS client module — schema |
| `transports/api/http/drizzle.config.ts` | 13 | API/WS client module — drizzle.config |
| `transports/api/http/lib/governed_bridge.ts` | 55 | Governed mutation bridge — TypeScript equivalent of transports/api/governed.py. |
| `transports/api/http/lib/python_bridge.ts` | 54 | API/WS client module — python bridge |
| `transports/api/http/middleware/auth.ts` | 34 | API/WS client module — auth |
| `transports/api/http/middleware/operator.ts` | 37 | API/WS client module — operator |
| `transports/api/http/package.json` | 30 | npm package manifest |
| `transports/api/http/routes/chat.ts` | 48 | API/WS client module — chat |
| `transports/api/http/routes/config.ts` | 45 | API/WS client module — config |
| `transports/api/http/routes/execution.ts` | 138 | API/WS client module — execution |
| `transports/api/http/routes/governance.ts` | 92 | API/WS client module — governance |
| `transports/api/http/routes/knowledge.ts` | 104 | API/WS client module — knowledge |
| `transports/api/http/routes/organism.ts` | 729 | API/WS client module — organism |
| `transports/api/http/routes/settings.ts` | 59 | API/WS client module — settings |
| `transports/api/http/routes/system.ts` | 260 | API/WS client module — system |
| `transports/api/http/server.ts` | 62 | API/WS client module — server |
| `transports/api/http/tsconfig.json` | 15 | TypeScript compiler configuration |
| `transports/api/http/types.ts` | 10 | Shared Hono Env type used by every route file and middleware. |
| `transports/api/invariants.py` | 149 | Invariant enforcement — validates substrate laws at every transition point. |
| `transports/api/operator.py` | 601 | UMH Operator Workstation API — FastAPI backend for the operator UI. |
| `transports/api/organism_bridge.py` | 2,538 | Organism runtime bridge — exposes organism subsystem state and actions |
| `transports/api/read_path_isolation.py` | 188 | Read-path isolation for hot Cockpit poll routes — P4S-31C runtime hardening. |
| `transports/api/runtime.py` | 90 | Control plane runtime — the top-level orchestrator that wires everything together. |
| `transports/api/runtime_state_routes.py` | 121 | Runtime State API routes — read-only workstation awareness. |
| `transports/api/signal_factory.py` | 32 | API signal factory — converts HTTP requests to SignalEnvelopes. |
| `transports/api/signal_router.py` | 208 | Signal router — enforces the legal processing pathway for all signals. |
| `transports/api/telemetry_routes.py` | 133 | Phase 15B: Execution Telemetry route handlers. |
| `transports/api/voice.py` | 507 | Voice session API — exposes the voice pipeline loop over HTTP. |
| `transports/api/webhooks/__init__.py` | 0 | package marker (empty) |
| `transports/api/webhooks/calendly_webhook.py` | 461 | — |
| `transports/api/workstation.py` | 137 | Workstation API — workstation mode execution, state, and health. |

## transports/channels/ (2 files)

| Path | Lines | Purpose |
|---|---|---|
| `transports/channels/__init__.py` | 0 | package marker (empty) |
| `transports/channels/channel.py` | 452 | EOS Channel System |

## transports/cli/ (8 files)

| Path | Lines | Purpose |
|---|---|---|
| `transports/cli/__init__.py` | 1 | UMH CLI — operator terminal interface. |
| `transports/cli/__main__.py` | 13 | Allow `python -m transports.cli` invocation. |
| `transports/cli/cli_voice.py` | 170 | CLI voice capture — Claude-Code-style /voice push-to-talk over the governed WS. |
| `transports/cli/client.py` | 126 | HTTP client for UMH API — transport layer, no substrate imports. |
| `transports/cli/commands.py` | 79 | Slash command dispatch for UMH CLI. |
| `transports/cli/display.py` | 171 | Rich display formatters for UMH CLI output. |
| `transports/cli/main.py` | 163 | UMH CLI — operator terminal interface. |
| `transports/cli/theme.py` | 62 | WorldView design tokens for terminal — matches cockpit/src/renderer/styles/tokens.css. |

## transports/discord/ (6 files)

| Path | Lines | Purpose |
|---|---|---|
| `transports/discord/__init__.py` | 0 | package marker (empty) |
| `transports/discord/approval_bridge.py` | 235 | Approval bridge — Discord interactive buttons for governance approvals. |
| `transports/discord/discord_utils.py` | 172 | discord_utils — single source of truth for all Discord posting from EOS. |
| `transports/discord/interface_adapter_v1.py` | 503 | Discord Interface Adapter v1. |
| `transports/discord/signal_factory.py` | 75 | Discord signal factory -- converts Discord messages to SignalEnvelopes. |
| `transports/discord/spine_integration_v1.py` | 276 | Discord Spine Integration v1. |

## transports/node_mesh/ (12 files)

| Path | Lines | Purpose |
|---|---|---|
| `transports/node_mesh/__init__.py` | 0 | package marker (empty) |
| `transports/node_mesh/config.py` | 201 | Node mesh configuration loader and token management. |
| `transports/node_mesh/integration/__init__.py` | 0 | package marker (empty) |
| `transports/node_mesh/integration/handlers.py` | 199 | Node mesh capability handler — proxies execution requests to remote nodes over WebSocket. |
| `transports/node_mesh/integration/manifest.py` | 19 | Build an IntegrationManifest for a connected mesh node. |
| `transports/node_mesh/integration/outcomes.py` | 53 | Node mesh outcome receiver — delivers outcomes to remote nodes. |
| `transports/node_mesh/integration/signals.py` | 57 | Node mesh signal emitter — declares signal types a remote node can emit. |
| `transports/node_mesh/integration/types.py` | 129 | Pure data types for the node mesh — no transport dependencies. |
| `transports/node_mesh/metrics_buffer.py` | 125 | Per-node ring buffer for telemetry metrics — bypasses the full pipeline. |
| `transports/node_mesh/registry.py` | 79 | Node registry — tracks connected mesh nodes and their state. |
| `transports/node_mesh/run.py` | 162 | Standalone launcher for the UMH Node Mesh server. |
| `transports/node_mesh/server.py` | 1,172 | Node Mesh WebSocket server — manages node connections and lifecycle. |

## transports/presence/ (23 files)

| Path | Lines | Purpose |
|---|---|---|
| `transports/presence/__init__.py` | 0 | package marker (empty) |
| `transports/presence/handlers/__init__.py` | 5 | Discord bot handler modules. |
| `transports/presence/handlers/cc_command_handler.py` | 563 | Inline command handlers for Discord on_message. |
| `transports/presence/handlers/intent_handler.py` | 437 | Intent classification and gateway routing. |
| `transports/presence/handlers/pipeline_handler.py` | 138 | Pipeline update detection and Notion stage updates. |
| `transports/presence/handlers/report_handlers.py` | 21 | Report handler functions — backward-compat re-export. |
| `transports/presence/handlers/reports/__init__.py` | 31 | Report handler package — re-exports all handler functions. |
| `transports/presence/handlers/reports/_common.py` | 53 | Shared imports and helpers for report handler modules. |
| `transports/presence/handlers/reports/adapter.py` | 220 | Adapter report handler. |
| `transports/presence/handlers/reports/capability.py` | 227 | Capability report handler. |
| `transports/presence/handlers/reports/constitution.py` | 321 | Constitution report handler. |
| `transports/presence/handlers/reports/continuity.py` | 285 | Continuity report handler. |
| `transports/presence/handlers/reports/economics.py` | 347 | Economics report handler. |
| `transports/presence/handlers/reports/epistemic.py` | 272 | Epistemic report handler. |
| `transports/presence/handlers/reports/federation.py` | 323 | Federation report handler. |
| `transports/presence/handlers/reports/governance_intelligence.py` | 298 | Governance intelligence report handler. |
| `transports/presence/handlers/reports/identity.py` | 288 | Identity report handler. |
| `transports/presence/handlers/reports/orchestration.py` | 254 | Orchestration report handler. |
| `transports/presence/handlers/reports/resilience.py` | 169 | Resilience report handler. |
| `transports/presence/handlers/reports/strategy.py` | 371 | Strategy report handler. |
| `transports/presence/handlers/reports/telos.py` | 305 | Telos report handler. |
| `transports/presence/handlers/substrate_command_handler.py` | 939 | Substrate command handler for the live Discord bot. |
| `transports/presence/handlers/voice_handler.py` | 22 | Voice handler — skeleton module. |
