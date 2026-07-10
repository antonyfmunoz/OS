---
type: codewiki-inventory
dir: substrate
source_sha: c806e75e29acfc82d1428de2ccc17924403407ab
---

# `substrate/` — File Inventory

**Files:** 1,009 regular + 0 symlinks · **Bytes:** 12,452,560

[Narrative page](../dirs/substrate.md)


## substrate/ (root)

| Path | Lines | Purpose |
|---|---|---|
| `substrate/__init__.py` | 501 | UMH Substrate — the unified intelligence substrate. |
| `substrate/canonical_types.py` | 1,532 | Canonical Type Registry — single source of truth for all UMH domain types. |
| `substrate/self_model.py` | 478 | Self-Model — the substrate's awareness of its own structure and state. |
| `substrate/types.py` | 1,553 | Canonical domain type system — SignalEnvelope, RiskClass, Modality and 30+ Pydantic models shared by every layer |

## substrate/composition/ (46 files)

| Path | Lines | Purpose |
|---|---|---|
| `substrate/composition/README.md` | 22 | composition/ |
| `substrate/composition/__init__.py` | 0 | package marker (empty) |
| `substrate/composition/knowledge_gap_trigger.py` | 170 | Knowledge gap trigger — detects gaps during execution and triggers composition. |
| `substrate/composition/mastery/__init__.py` | 0 | package marker (empty) |
| `substrate/composition/mastery/authoring/__init__.py` | 21 | Tool Mastery Author Agent. |
| `substrate/composition/mastery/authoring/__main__.py` | 4 | python -m entrypoint for the mastery authoring CLI |
| `substrate/composition/mastery/authoring/agent.py` | 188 | Author Agent orchestrator. |
| `substrate/composition/mastery/authoring/cli.py` | 132 | CLI entry for the Tool Mastery Author Agent. |
| `substrate/composition/mastery/authoring/draft.py` | 451 | Draft authored section content from SectionEvidence. |
| `substrate/composition/mastery/authoring/loader.py` | 218 | Research artifact loader. |
| `substrate/composition/mastery/authoring/mapping.py` | 609 | Section → raw-capture evidence mapping. |
| `substrate/composition/mastery/authoring/models.py` | 140 | Data types for the Tool Mastery Author Agent. |
| `substrate/composition/mastery/authoring/paths.py` | 16 | Path resolution for the Tool Mastery Author Agent. |
| `substrate/composition/mastery/authoring/reconcile.py` | 172 | Reconcile drafts with existing on-disk skill files. |
| `substrate/composition/mastery/authoring/verify.py` | 77 | Run verify_tool_skill.py against an authored tool. |
| `substrate/composition/mastery/management/__init__.py` | 74 | Tool Mastery Manager — unification layer over the Tool Mastery Engine. |
| `substrate/composition/mastery/management/active_tool_context.py` | 150 | Active Tool Context for the Tool Mastery Engine. |
| `substrate/composition/mastery/management/backlog.py` | 188 | Backlog / bootstrap flow. |
| `substrate/composition/mastery/management/coverage.py` | 120 | Unified coverage evaluator for the Tool Mastery Manager. |
| `substrate/composition/mastery/management/discovery.py` | 332 | Tool discovery for the Tool Mastery Manager. |
| `substrate/composition/mastery/management/ensure.py` | 174 | ensure_mastery — the primary entry point of the Tool Mastery Manager. |
| `substrate/composition/mastery/management/maintenance.py` | 60 | Maintenance flows for the Tool Mastery Manager. |
| `substrate/composition/mastery/management/mastery_assurance.py` | 265 | Mastery Assurance Gate for the Tool Mastery Engine. |
| `substrate/composition/mastery/management/models.py` | 121 | Data types for the Tool Mastery Manager. |
| `substrate/composition/mastery/management/paths.py` | 20 | Path resolution for the Tool Mastery Manager. |
| `substrate/composition/mastery/management/tool_mastery_resolver.py` | 325 | Natural Language Tool Mastery Resolver. |
| `substrate/composition/mastery/research/__init__.py` | 43 | Tool Mastery Research Agent. |
| `substrate/composition/mastery/research/__main__.py` | 4 | python -m entrypoint for the mastery research CLI |
| `substrate/composition/mastery/research/agent.py` | 201 | Research Agent orchestrator. |
| `substrate/composition/mastery/research/artifact.py` | 608 | Artifact writer for the Tool Mastery Research Agent. |
| `substrate/composition/mastery/research/candidate_approval.py` | 271 | Candidate approval gate for search-based source discovery. |
| `substrate/composition/mastery/research/cli.py` | 249 | CLI entry for the Tool Mastery Research Agent. |
| `substrate/composition/mastery/research/docs_site_discovery.py` | 611 | Docs site discovery for the Tool Mastery Research Agent. |
| `substrate/composition/mastery/research/extraction.py` | 1,265 | Structured knowledge extraction for the Tool Mastery Research Agent. |
| `substrate/composition/mastery/research/fetcher.py` | 165 | Fetcher for the Tool Mastery Research Agent. |
| `substrate/composition/mastery/research/github_extractor.py` | 350 | GitHub repo extractor for the Tool Mastery Research Agent. |
| `substrate/composition/mastery/research/handoff.py` | 123 | Safe metadata handoff for the Tool Mastery Research Agent. |
| `substrate/composition/mastery/research/headless_fetcher.py` | 366 | Headless rendering fetch path for the Tool Mastery Research Agent. |
| `substrate/composition/mastery/research/models.py` | 209 | Data types for the Tool Mastery Research Agent. |
| `substrate/composition/mastery/research/paths.py` | 17 | Path resolution for the Tool Mastery Research Agent. |
| `substrate/composition/mastery/research/search_discovery.py` | 353 | Deterministic search candidate generator for the Research Agent. |
| `substrate/composition/mastery/research/source_discovery.py` | 362 | Source discovery for the Tool Mastery Research Agent. |
| `substrate/composition/mastery/research/source_quality.py` | 370 | Source quality scoring for the Tool Mastery Research Agent. |
| `substrate/composition/mastery/research/structured_crawl.py` | 438 | Structured crawl expansion for the Tool Mastery Research Agent. |
| `substrate/composition/registries/__init__.py` | 0 | package marker (empty) |
| `substrate/composition/registries/canonical_command_registry_v1.py` | 425 | Canonical Command Registry v1. |

## substrate/contracts/ (12 files)

| Path | Lines | Purpose |
|---|---|---|
| `substrate/contracts/__init__.py` | 21 | Substrate contracts — canonical Protocol interfaces for the UMH substrate. |
| `substrate/contracts/adapter_contracts.py` | 64 | Adapter registry contracts — substrate-owned interface for adapter descriptors. |
| `substrate/contracts/agent_runtime_contracts.py` | 40 | Agent runtime protocol — substrate-owned interface for LLM execution. |
| `substrate/contracts/agent_types.py` | 114 | Canonical agent types owned by the substrate layer. |
| `substrate/contracts/control_plane_protocol.py` | 24 | Control plane protocol — canonical contracts for control plane subsystems. |
| `substrate/contracts/execution_protocol.py` | 13 | Execution protocol — canonical contracts for the execution pipeline. |
| `substrate/contracts/governance_protocol.py` | 11 | Governance protocol — canonical contract for governance engines. |
| `substrate/contracts/infrastructure_protocol.py` | 17 | Infrastructure protocol — canonical contracts for substrate storage and projection. |
| `substrate/contracts/integration_protocol.py` | 29 | Integration protocol — canonical contracts for integration-side adapters. |
| `substrate/contracts/organism_protocol.py` | 28 | Organism protocol — canonical contracts for the agent society layer. |
| `substrate/contracts/routing_contracts.py` | 50 | Routing contracts — substrate-owned capability classes and routing types. |
| `substrate/contracts/understanding_protocol.py` | 11 | Understanding protocol — canonical contracts for domain bridges and sources. |

## substrate/control_plane/ (77 files)

| Path | Lines | Purpose |
|---|---|---|
| `substrate/control_plane/__init__.py` | 0 | package marker (empty) |
| `substrate/control_plane/actions/__init__.py` | 0 | package marker (empty) |
| `substrate/control_plane/actions/actions.py` | 84 | Action object — the canonical unit of control in EOS. |
| `substrate/control_plane/actions/control_plane.py` | 272 | Control Plane — the public entry point for the EOS Action System. |
| `substrate/control_plane/actions/deferred.py` | 98 | Durable persistence for deferred actions. |
| `substrate/control_plane/actions/deferred_status.py` | 241 | Lightweight status tracking for deferred actions. |
| `substrate/control_plane/actions/executor.py` | 133 | Action executors — dispatch by action.type. |
| `substrate/control_plane/actions/idempotency.py` | 297 | Filesystem sentinel store for Control Plane idempotency. |
| `substrate/control_plane/actions/logging.py` | 74 | Append-only JSONL loggers for execution and decision records. |
| `substrate/control_plane/actions/notifier.py` | 121 | Notifier foundation for deferred actions. |
| `substrate/control_plane/actions/policy.py` | 164 | Policy bridge between the Control Plane and `runtime.authority_engine`. |
| `substrate/control_plane/actions/tme.py` | 140 | Tool Mastery Engine / Manager integration for the Control Plane. |
| `substrate/control_plane/actions/validator.py` | 187 | Validation + approval rules for Actions. |
| `substrate/control_plane/agents/__init__.py` | 0 | package marker (empty) |
| `substrate/control_plane/agents/agent_hierarchy.py` | 466 | Agent hierarchy — formal authority structure from founder down; resolves venture display names from instance config |
| `substrate/control_plane/agents/agent_teams.py` | 527 | Domain team registry for the OS agent system. |
| `substrate/control_plane/agents/ceo_agent.py` | 376 | CEOAgent — one per company, strategy layer. |
| `substrate/control_plane/agents/ceo_intelligence.py` | 726 | CEO Intelligence — real-time business diagnostics. |
| `substrate/control_plane/agents/ceo_operational_standards.py` | 603 | CEO Best Practices — operational ruleset for |
| `substrate/control_plane/agents/ea_operational_standards.py` | 142 | EA Best Practices — world class EA operating standards |
| `substrate/control_plane/context/__init__.py` | 92 | ContextAssembler — builds execution context from signal + identity. |
| `substrate/control_plane/context/context_builder.py` | 552 | ContextBuilder — single-pass context assembly for the execution spine. |
| `substrate/control_plane/context/context_compaction.py` | 213 | ContextCompactor — seamless context window management for long conversations. |
| `substrate/control_plane/coordination/__init__.py` | 0 | package marker (empty) |
| `substrate/control_plane/coordination/coordination_engine.py` | 387 | CoordinationEngine — event-driven task coordination for AI agents and humans. |
| `substrate/control_plane/delegation/__init__.py` | 0 | package marker (empty) |
| `substrate/control_plane/delegation/delegation_tracker.py` | 94 | Delegation Tracker — tracks tasks routed to CEO agents |
| `substrate/control_plane/events/__init__.py` | 0 | package marker (empty) |
| `substrate/control_plane/events/event_bus.py` | 671 | EventBus — reactive coordination layer for UMH agents. |
| `substrate/control_plane/events/event_manager.py` | 254 | Event Manager — coordinates conferences, offsites, client dinners, |
| `substrate/control_plane/goals/__init__.py` | 0 | package marker (empty) |
| `substrate/control_plane/goals/goal_selector.py` | 1,485 | GoalSelector — goal selection + system focus layer. |
| `substrate/control_plane/governance.py` | 278 | GovernanceEngine — the single governance entry point for UMH. |
| `substrate/control_plane/identity/__init__.py` | 69 | Identity resolution for the substrate control plane. |
| `substrate/control_plane/identity/ai_identity.py` | 267 | AIIdentityEngine — foundational AI identity principles. |
| `substrate/control_plane/invariants/__init__.py` | 0 | package marker (empty) |
| `substrate/control_plane/invariants/coherence_gate.py` | 74 | Coherence Gate — fail-closed execution guard. |
| `substrate/control_plane/invariants/spine_coherence_validator.py` | 233 | Canonical Spine Coherence Validator. |
| `substrate/control_plane/invariants/spine_lineage_contracts.py` | 189 | Canonical Spine Lineage Contracts. |
| `substrate/control_plane/memory.py` | 99 | MemorySystem — unified protocol over existing memory stores. |
| `substrate/control_plane/onboarding/__init__.py` | 0 | package marker (empty) |
| `substrate/control_plane/onboarding/onboarding_engine.py` | 357 | OnboardingEngine — conversational onboarding for new EOS founders. |
| `substrate/control_plane/onboarding/setup_wizard.py` | 166 | SetupWizard — onboarding flow for new EOS users. |
| `substrate/control_plane/orchestrator/__init__.py` | 0 | package marker (empty) |
| `substrate/control_plane/orchestrator/orchestrator.py` | 1,916 | Orchestrator — strategic intelligence layer. |
| `substrate/control_plane/proactive/__init__.py` | 0 | package marker (empty) |
| `substrate/control_plane/proactive/proactive_engine.py` | 301 | ProactiveIntelligenceEngine — surfaces what matters without being asked. |
| `substrate/control_plane/registry.py` | 105 | ComponentRegistry — unified registry for all substrate components. |
| `substrate/control_plane/router/__init__.py` | 111 | SignalRouter — the integration point that wires all subsystems together. |
| `substrate/control_plane/router/control_plane_router_v1.py` | 520 | Control Plane Router v1. |
| `substrate/control_plane/router/intent_router.py` | 170 | IntentRouter — classify founder messages to the correct agent domain. |
| `substrate/control_plane/router/router_contracts.py` | 167 | Control plane router contracts for the UMH substrate layer. |
| `substrate/control_plane/runtime/__init__.py` | 0 | package marker (empty) |
| `substrate/control_plane/runtime/cognitive_loop.py` | 1,740 | CognitiveLoop — full Perceive → Understand → Plan → Execute |
| `substrate/control_plane/runtime/gateway.py` | 1,946 | Gateway — single control plane for all AI operations. |
| `substrate/control_plane/runtime/orchestrator/__init__.py` | 0 | package marker (empty) |
| `substrate/control_plane/runtime/orchestrator/decisions.py` | 166 | Decision helpers for signal handler workflows. |
| `substrate/control_plane/runtime/orchestrator/handlers.py` | 321 | Signal handler workflows. |
| `substrate/control_plane/runtime/orchestrator/loop.py` | 454 | Autonomous loop — deterministic orchestration cycle. |
| `substrate/control_plane/runtime/orchestrator/orchestrator.py` | 201 | Orchestrator — execution coordinator for named workflows. |
| `substrate/control_plane/runtime/orchestrator/pipeline.py` | 276 | Pipeline — sequential composition of Control Plane actions. |
| `substrate/control_plane/runtime/orchestrator/signals.py` | 210 | Signals — filesystem-backed event layer for the orchestrator. |
| `substrate/control_plane/runtime/orchestrator/steps.py` | 210 | Reusable orchestrator step helpers. |
| `substrate/control_plane/runtime/orchestrator/workflows.py` | 124 | Workflow registry — wires existing Control Plane workflows into the orchestrator. |
| `substrate/control_plane/runtime/substrate_gateway.py` | 178 | SubstrateGateway — unified SignalEnvelope interface over the internal Gateway. |
| `substrate/control_plane/scheduling/__init__.py` | 0 | package marker (empty) |
| `substrate/control_plane/scheduling/daily_sync.py` | 631 | DailySync — structured daily briefing format. |
| `substrate/control_plane/scheduling/ideal_week.py` | 258 | Ideal Week — stores and applies the founder's ideal |
| `substrate/control_plane/scheduling/personal_admin.py` | 139 | Personal Admin — important dates, gift research, |
| `substrate/control_plane/scheduling/week_architect.py` | 95 | WeekArchitect — designs the upcoming week using the Ideal Week |
| `substrate/control_plane/signals/__init__.py` | 0 | package marker (empty) |
| `substrate/control_plane/signals/signal_hierarchy.py` | 249 | SignalHierarchyEngine — ranks signal before the filter applies. |
| `substrate/control_plane/strategy/__init__.py` | 0 | package marker (empty) |
| `substrate/control_plane/strategy/portfolio_advisor.py` | 799 | Portfolio Advisor — board-level intelligence across all companies in the portfolio. |
| `substrate/control_plane/strategy/portfolio_advisor_standards.py` | 486 | Portfolio Advisor Best Practices — operational |
| `substrate/control_plane/strategy/strategy_engine.py` | 525 | StrategyEngine — first-principles strategic reasoning layer. |
| `substrate/control_plane/strategy/task_yield_matrix.py` | 174 | Task Yield Matrix — task delegation audit framework. |

## substrate/execution/ (176 files)

| Path | Lines | Purpose |
|---|---|---|
| `substrate/execution/__init__.py` | 0 | package marker (empty) |
| `substrate/execution/actuation/__init__.py` | 0 | package marker (empty) |
| `substrate/execution/actuation/actuator_backend_registry_v1.py` | 286 | Actuator Backend Registry v1. |
| `substrate/execution/actuation/actuator_maturity_v1.py` | 134 | Actuator Maturity Model v1. |
| `substrate/execution/actuation/observed_desktop_state_v1.py` | 133 | Observed Desktop State v1. |
| `substrate/execution/actuation/windows_foreground_actuator_v1.py` | 314 | Windows Foreground Actuator v1 (Maturity-Aware). |
| `substrate/execution/adapters/__init__.py` | 0 | package marker (empty) |
| `substrate/execution/adapters/physical.py` | 347 | Physical Adapter Framework — hardware and IoT extension points. |
| `substrate/execution/agents/__init__.py` | 0 | package marker (empty) |
| `substrate/execution/agents/browser_agent.py` | 562 | BrowserAgent — Playwright-based web operator for EOS agents. |
| `substrate/execution/agents/computer_use_agent.py` | 330 | Computer-Use Agent — governed visual automation across execution layers. |
| `substrate/execution/bridge/__init__.py` | 65 | execution.bridge — Lazy-import package. |
| `substrate/execution/bridge/actions.py` | 118 | SafeAction schema — structured intents for future local execution. |
| `substrate/execution/bridge/app_allowlist.py` | 70 | App launch allow-list for LAUNCH_APP actions. |
| `substrate/execution/bridge/audio_loop.py` | 612 | Audio loop — bounded local interaction-window model. |
| `substrate/execution/bridge/auto_task_generation.py` | 290 | Auto-task generation — bridges the perception layer to the task system. |
| `substrate/execution/bridge/browser_agent.py` | 495 | Browser agent — real Playwright execution surface for the substrate. |
| `substrate/execution/bridge/capabilities.py` | 80 | Capability abstraction — what a node can do. |
| `substrate/execution/bridge/capability_routing.py` | 230 | Capability-aware task routing — deterministic target selection. |
| `substrate/execution/bridge/capability_tagging.py` | 133 | Capability tagging — additive pre-routing layer. |
| `substrate/execution/bridge/claude_responder.py` | 178 | Claude Responder v1 — thin adapter that turns a text prompt into a reply by |
| `substrate/execution/bridge/claude_session_bridge.py` | 1,185 | Claude Code Session Bridge v1 — persistent tmux-backed Claude Code sessions. |
| `substrate/execution/bridge/context_lifecycle.py` | 313 | Context lifecycle — pressure-aware session maintenance with checkpoint/restore. |
| `substrate/execution/bridge/day_workflows.py` | 570 | Day workflow coordination — open_day / close_day. |
| `substrate/execution/bridge/discord_mode_routing.py` | 336 | Discord Channel Mode Routing v1 — bounded channel→mode classification. |
| `substrate/execution/bridge/discord_output_policy.py` | 15 | Display-name policy for Discord watcher output. |
| `substrate/execution/bridge/discord_text_transport.py` | 1,653 | Discord text transport — Pseudo-Live Voice Loop v1. |
| `substrate/execution/bridge/discord_voice_playback.py` | 651 | Discord voice playback — bounded TTS adapter on top of the transport. |
| `substrate/execution/bridge/discord_voice_transport.py` | 804 | Discord voice transport — bounded adapter onto the existing voice substrate. |
| `substrate/execution/bridge/event_spine.py` | 206 | Event Spine — unified structured event model for EOS substrate. |
| `substrate/execution/bridge/execution_trace.py` | 300 | Execution trace for EOS request lifecycle. |
| `substrate/execution/bridge/live_sessions.py` | 634 | Live sessions — real-time continuous interaction layer for the substrate. |
| `substrate/execution/bridge/local_control.py` | 946 | Local control — safe OS-level action layer for the local machine. |
| `substrate/execution/bridge/local_listener.py` | 396 | Local listener — bounded wake/activation layer for the substrate. |
| `substrate/execution/bridge/memory_scope_contracts.py` | 96 | Memory scope contracts. |
| `substrate/execution/bridge/mode_behavior.py` | 259 | Mode behavior shaping — post-router output shaping by substrate mode. |
| `substrate/execution/bridge/node_controller.py` | 357 | NodeController — unified routing brain for task→node dispatch. |
| `substrate/execution/bridge/node_transport.py` | 290 | NodeTransport — aiohttp transport adapter for local station daemon. |
| `substrate/execution/bridge/nodes.py` | 245 | Node abstraction — execution targets beyond "the VPS". |
| `substrate/execution/bridge/operator_presence.py` | 119 | Operator presence — tiny deterministic hybrid intro/outro templates. |
| `substrate/execution/bridge/operator_session.py` | 299 | Operator session spine — single authoritative source of truth for the |
| `substrate/execution/bridge/operator_state.py` | 393 | Operator state — bounded unified state model for the workstation operator. |
| `substrate/execution/bridge/operator_transitions.py` | 481 | Operator transitions — deterministic state transition layer. |
| `substrate/execution/bridge/perception.py` | 997 | Perception layer — ambient sensing of system and environment state. |
| `substrate/execution/bridge/pipeline_execution.py` | 740 | Pipeline execution engine — step-level execution, retry, and resume. |
| `substrate/execution/bridge/playback_status.py` | 92 | Shared playback status snapshot shape for voice transports. |
| `substrate/execution/bridge/resource_guard.py` | 272 | Resource Guard v1 — pre-execution VPS resource check. |
| `substrate/execution/bridge/result_query.py` | 454 | Result query helpers — tiny operator-facing view over the ResultStore. |
| `substrate/execution/bridge/result_store.py` | 245 | ResultStore — durable index of ingested ActionResults. |
| `substrate/execution/bridge/ritual_body.py` | 341 | Ritual body — tiny executable layer for open_day / close_day. |
| `substrate/execution/bridge/ritual_inference.py` | 198 | Ritual hint inference — infer a scene hint when the operator did not |
| `substrate/execution/bridge/ritual_runner.py` | 217 | Ritual runner — shell-callable entry points for open_day / close_day. |
| `substrate/execution/bridge/rituals.py` | 213 | Ritual workflow scaffold — open_day / close_day. |
| `substrate/execution/bridge/roles.py` | 155 | Agent role abstraction — clean contract for multi-agent orchestration. |
| `substrate/execution/bridge/scene_capabilities.py` | 172 | Scene → capability requirements — tiny explicit mapping. |
| `substrate/execution/bridge/scene_policy.py` | 243 | Scene policy — deterministic mapping from (node, readiness, hint) → scene. |
| `substrate/execution/bridge/scenes.py` | 180 | Scene registry — small, code-declared workstation bootstrap recipes. |
| `substrate/execution/bridge/session_control.py` | 261 | Session control — lifecycle commands for Claude Code tmux sessions. |
| `substrate/execution/bridge/session_discord_bridge.py` | 462 | Session Discord Bridge — routes SessionWatcher events to Discord and back. |
| `substrate/execution/bridge/session_watcher.py` | 746 | Session Watcher — continuous tmux state machine for Claude Code sessions. |
| `substrate/execution/bridge/station.py` | 227 | Station Daemon contract. |
| `substrate/execution/bridge/station_bus.py` | 189 | StationBus — MVP transport between EOS and local Station Daemons. |
| `substrate/execution/bridge/station_daemon.py` | 869 | StationDaemon — minimal local node execution loop. |
| `substrate/execution/bridge/station_helpers.py` | 127 | Small helpers for proposing MVP SafeActions to a named station. |
| `substrate/execution/bridge/station_presence.py` | 334 | Station presence — unified station posture and availability state. |
| `substrate/execution/bridge/station_readiness.py` | 305 | Station readiness — derived view of whether a node is fit for ritual work. |
| `substrate/execution/bridge/storage.py` | 213 | Substrate storage — minimal persistence for NodeRegistry and RitualRegistry. |
| `substrate/execution/bridge/target_policy.py` | 213 | Hybrid Execution Target Policy v1 — deterministic target resolution. |
| `substrate/execution/bridge/task_decomposition.py` | 224 | Deterministic task decomposition — breaks tasks into ordered pipeline steps. |
| `substrate/execution/bridge/task_execution.py` | 504 | Real task execution pipeline — binds tasks to tmux-backed Claude sessions. |
| `substrate/execution/bridge/task_pipeline.py` | 480 | Task pipeline data model — ordered multi-step execution for tasks. |
| `substrate/execution/bridge/task_queue.py` | 244 | Priority queue layer for the task system. |
| `substrate/execution/bridge/task_system.py` | 601 | Task autonomy and overnight execution system (v1). |
| `substrate/execution/bridge/transcript_inject.py` | 204 | Transcript injection — the bounded entry point for text-shaped input |
| `substrate/execution/bridge/tts_sanitize.py` | 186 | TTS reply sanitization — strip Claude Code / provider footer noise. |
| `substrate/execution/bridge/voice_eos_responder.py` | 338 | Voice → EOS responder bridge. |
| `substrate/execution/bridge/voice_first.py` | 434 | Voice-first response orchestration. |
| `substrate/execution/bridge/voice_session.py` | 490 | Voice session — bounded live voice-presence layer for the substrate. |
| `substrate/execution/bridge/wake_producer.py` | 490 | Wake producer — bounded wake-word / clap activation layer for the substrate. |
| `substrate/execution/bridge/workflow_delegation.py` | 473 | Workflow Delegation Layer v1 — deterministic intent classification + policy. |
| `substrate/execution/bridge/workflow_execution.py` | 361 | Workflow Execution Layer v1.1 — bounded, deterministic workflow handlers. |
| `substrate/execution/bridge/workload_policy.py` | 192 | Workload Classification Policy v1 — deterministic execution weight. |
| `substrate/execution/cpu_gate.py` | 216 | Universal CPU gate — single choke point for all UMH execution paths. |
| `substrate/execution/credential_gate.py` | 308 | Credential injection gate — validates credentials flow through 1Password. |
| `substrate/execution/executor.py` | 186 | Work packet executor — the governed execution pipeline. |
| `substrate/execution/feedback.py` | 85 | FeedbackCapture — captures execution quality signals. |
| `substrate/execution/feedback_loop.py` | 491 | RLHF Feedback Loop — explicit human feedback ingestion and learning cycle. |
| `substrate/execution/ingestion/__init__.py` | 46 | Canonical ingestion pipeline — substrate.execution.ingestion. |
| `substrate/execution/intent/__init__.py` | 38 | UMH MVP intent → proof operating loop (P4S-31). |
| `substrate/execution/intent/intent_spec.py` | 216 | IntentSpec — the typed, deterministic capture of one bounded operator intent. |
| `substrate/execution/intent/loop.py` | 543 | IntentLoop — the thinnest UMH operating-loop state machine. |
| `substrate/execution/logs/instagram_login_error.png` | — | png asset (271,431 B) |
| `substrate/execution/loop/__init__.py` | 17 | Persistent execution loops — config-driven autonomous cycles for UMH. |
| `substrate/execution/loop/execution_loop.py` | 328 | ExecutionLoop — closed-loop goal execution with outcome feedback. |
| `substrate/execution/loop/persistent_loop.py` | 407 | PersistentLoop — config-driven runtime loops for UMH. |
| `substrate/execution/loop/stages.py` | 274 | Built-in loop stages — composable pipeline steps for persistent loops. |
| `substrate/execution/mastery_gate.py` | 151 | Mastery Gate — mandatory pipeline check before execution. |
| `substrate/execution/media/__init__.py` | 0 | package marker (empty) |
| `substrate/execution/media/media_processor.py` | 898 | MediaProcessor — unified multimodal file handler. |
| `substrate/execution/mesh_verdict.py` | 193 | Mesh verdict token — signed governance verdicts for remote node dispatch. |
| `substrate/execution/pipeline.py` | 557 | ExecutionPipeline — the master success loop. |
| `substrate/execution/proof_generator.py` | 101 | Proof generator — creates verifiable proof artifacts from execution results. |
| `substrate/execution/queue.py` | 80 | Execution queue — ordered, priority-aware queue for work packets. |
| `substrate/execution/runtime/__init__.py` | 0 | package marker (empty) |
| `substrate/execution/runtime/capability_router.py` | 724 | capability_router — Intent-driven tool selection for UMH. |
| `substrate/execution/runtime/execution_contracts_v1.py` | 568 | Execution Contracts v1 for the canonical runtime spine. |
| `substrate/execution/runtime/execution_spine.py` | 228 | ExecutionSpine — single execution path for all EOS operations (legacy runtime). |
| `substrate/execution/runtime/live_local_runtime_execution_v1.py` | 464 | Live Local Runtime Execution v1 for the UMH substrate layer. |
| `substrate/execution/runtime/local_runtime_supervisor_v1.py` | 615 | Local Runtime Supervisor v1 for the UMH substrate layer. |
| `substrate/execution/runtime/node_sync_gate_v1.py` | 670 | Node Sync Gate v1 for the UMH substrate layer. |
| `substrate/execution/runtime/runtime_bootstrap_state_v1.py` | 260 | Runtime Bootstrap State v1. |
| `substrate/execution/runtime/runtime_dispatch_queue_v1.py` | 195 | Runtime Dispatch Queue v1 for the UMH substrate layer. |
| `substrate/execution/runtime/runtime_execution_result_v1.py` | 138 | Runtime Execution Result v1 — proof-bearing execution result type. |
| `substrate/execution/runtime/runtime_heartbeat_v1.py` | 123 | Runtime Heartbeat v1 for the UMH substrate layer. |
| `substrate/execution/runtime/runtime_presence_state_v1.py` | 73 | Runtime Presence State v1 — workstation presence tracking. |
| `substrate/execution/runtime/runtime_recovery_v1.py` | 222 | Runtime Recovery v1 for the UMH substrate layer. |
| `substrate/execution/runtime/runtime_session_registry_v1.py` | 163 | Runtime Session Registry v1 for the UMH substrate layer. |
| `substrate/execution/runtime/substrate_continuity_engine_v1.py` | 295 | Substrate Continuity Engine v1. |
| `substrate/execution/runtime/worker_runtime_contracts.py` | 140 | Worker runtime contracts for the UMH substrate layer. |
| `substrate/execution/runtime/worker_supervisor_v1.py` | 398 | Worker Supervisor v1 for the UMH substrate layer. |
| `substrate/execution/runtime/workpacket_execution_gate_v1.py` | 659 | WorkPacket Execution Gate v1 for the UMH substrate layer. |
| `substrate/execution/spine.py` | 546 | ExecutionSpine — the 8-stage execution pipeline. |
| `substrate/execution/trace.py` | 126 | TraceRecorder — records execution traces for every signal lifecycle. |
| `substrate/execution/understanding_bridge.py` | 311 | Understanding Bridge — wires the understanding layer into the execution pipeline. |
| `substrate/execution/voice/__init__.py` | 0 | package marker (empty) |
| `substrate/execution/voice/canonical_voice_runtime.py` | 95 | Canonical voice runtime — the single declared voice-session entry. |
| `substrate/execution/voice/error_codes.py` | 96 | Canonical voice error taxonomy — the ONE voice error enum, tree-wide. |
| `substrate/execution/voice/session.py` | 511 | Voice Session — the ONE canonical voice runtime. |
| `substrate/execution/voice/store.py` | 496 | Canonical voice record store — the ONE durable home for voice sessions. |
| `substrate/execution/voice/tts_chain.py` | 139 | TTS provider chain — free-first, graceful fallback, always produces audio. |
| `substrate/execution/voice/voice_engine.py` | 640 | VoiceEngine — intelligent voice layer for Discord. |
| `substrate/execution/voice/warm_engine.py` | 74 | Warm VoiceEngine singleton — one preloaded STT/TTS engine, process-wide. |
| `substrate/execution/workers/__init__.py` | 0 | package marker (empty) |
| `substrate/execution/workers/workstation/__init__.py` | 0 | package marker (empty) |
| `substrate/execution/workers/workstation/_dormant/__init__.py` | 0 | package marker (empty) |
| `substrate/execution/workers/workstation/_dormant/adapter_autogeneration_engine_v1.py` | 992 | Adapter Autogeneration Engine v1. |
| `substrate/execution/workers/workstation/_dormant/adaptive_governance_intelligence_engine_v1.py` | 1,350 | Adaptive Governance Intelligence Engine v1. |
| `substrate/execution/workers/workstation/_dormant/browser_continuity_bridge_v1.py` | 275 | Browser Continuity Bridge v1. |
| `substrate/execution/workers/workstation/_dormant/browser_execution_orchestrator_v1.py` | 225 | Browser Execution Orchestrator v1. |
| `substrate/execution/workers/workstation/_dormant/browser_gui_contracts_v1.py` | 510 | Browser and GUI Embodiment Contracts v1. |
| `substrate/execution/workers/workstation/_dormant/browser_gui_embodiment_engine_v1.py` | 245 | Browser and GUI Embodiment Engine v1. |
| `substrate/execution/workers/workstation/_dormant/browser_observability_pipeline_v1.py` | 153 | Browser Observability Pipeline v1. |
| `substrate/execution/workers/workstation/_dormant/browser_operational_modes_v1.py` | 237 | Browser Operational Modes v1. |
| `substrate/execution/workers/workstation/_dormant/browser_replay_validator_v1.py` | 259 | Browser Replay Validator v1. |
| `substrate/execution/workers/workstation/_dormant/constitutional_antifragility_resilience_engine_v1.py` | 1,241 | Constitutional Antifragility and Evolutionary Resilience v1. |
| `substrate/execution/workers/workstation/_dormant/constitutional_epistemic_intelligence_engine_v1.py` | 1,512 | Constitutional Epistemic Intelligence and Reality Coherence Engine v1. |
| `substrate/execution/workers/workstation/_dormant/constitutional_identity_continuity_engine_v1.py` | 1,494 | Constitutional Identity Continuity and Sovereign Memory Architecture v1. |
| `substrate/execution/workers/workstation/_dormant/constitutional_resource_economics_engine_v1.py` | 1,262 | Constitutional Resource Economics and Coordination Engine v1. |
| `substrate/execution/workers/workstation/_dormant/constitutional_strategic_intelligence_engine_v1.py` | 1,852 | Constitutional Strategic Intelligence and Recursive Leverage Planning Engine v1. |
| `substrate/execution/workers/workstation/_dormant/constitutional_substrate_governance_layer_v1.py` | 1,559 | Constitutional Substrate Governance Layer v1. |
| `substrate/execution/workers/workstation/_dormant/constitutional_telos_alignment_engine_v1.py` | 1,381 | Constitutional Telos Alignment and Purpose Governance v1. |
| `substrate/execution/workers/workstation/_dormant/distributed_constitutional_substrate_federation_v1.py` | 1,444 | Distributed Constitutional Substrate Federation v1. |
| `substrate/execution/workers/workstation/_dormant/governed_browser_adapter_v1.py` | 450 | Governed Browser Adapter v1. |
| `substrate/execution/workers/workstation/_dormant/governed_recursive_orchestration_engine_v1.py` | 1,464 | Governed Recursive Orchestration Engine v1. |
| `substrate/execution/workers/workstation/_dormant/persistent_substrate_continuity_engine_v1.py` | 1,469 | Persistent Substrate Continuity Engine v1. |
| `substrate/execution/workers/workstation/_dormant/recursive_capability_planning_engine_v1.py` | 1,313 | Recursive Capability Planning Engine v1. |
| `substrate/execution/workers/workstation/_dormant/visible_gui_adapter_v1.py` | 282 | Visible GUI Adapter v1. |
| `substrate/execution/workers/workstation/_dormant/workstation_operational_embodiment_engine_v1.py` | 316 | Workstation Operational Embodiment Engine v1. |
| `substrate/execution/workers/workstation/_dormant/workstation_relay_heartbeat_v1.py` | 158 | Workstation Relay Heartbeat v1. |
| `substrate/execution/workers/workstation/_dormant/workstation_relay_node_v1.py` | 130 | Workstation Relay Node v1. |
| `substrate/execution/workers/workstation/_dormant/workstation_relay_proof_v1.py` | 97 | Workstation Relay Proof v1. |
| `substrate/execution/workers/workstation/_dormant/workstation_replay_validator_v1.py` | 286 | Workstation Replay Validator v1. |
| `substrate/execution/workers/workstation/_dormant/workstation_state_registry_v1.py` | 212 | Workstation State Registry v1. |
| `substrate/execution/workers/workstation/environment_mapping_engine_v1.py` | 1,124 | Environment Mapping Engine v1. |
| `substrate/execution/workers/workstation/foreground_cu_ingestion_execution_v1.py` | 575 | Foreground CU Ingestion Execution v1. |
| `substrate/execution/workers/workstation/governed_shell_adapter_v1.py` | 381 | Governed Shell Adapter v1. |
| `substrate/execution/workers/workstation/relay_execution_transport_v1.py` | 285 | Relay Execution Transport v1. |
| `substrate/execution/workers/workstation/tmux_operational_adapter_v1.py` | 266 | Tmux Operational Adapter v1. |
| `substrate/execution/workers/workstation/visible_actuation_proof_v1.py` | 285 | Visible Actuation Proof v1. |
| `substrate/execution/workers/workstation/workstation_continuity_bridge_v1.py` | 306 | Workstation Continuity Bridge v1. |
| `substrate/execution/workers/workstation/workstation_contracts_v1.py` | 485 | Workstation Contracts v1 for operational embodiment. |
| `substrate/execution/workers/workstation/workstation_execution_orchestrator_v1.py` | 189 | Workstation Execution Orchestrator v1. |
| `substrate/execution/workers/workstation/workstation_node_registry_v1.py` | 108 | Workstation Node Registry v1. |
| `substrate/execution/workers/workstation/workstation_observability_pipeline_v1.py` | 134 | Workstation Observability Pipeline v1. |
| `substrate/execution/workers/workstation/workstation_operational_modes_v1.py` | 210 | Workstation Operational Modes v1. |
| `substrate/execution/workers/workstation/workstation_relay_self_heal_v1.py` | 160 | Workstation Relay Self-Heal v1. |

## substrate/foundation/ (4 files)

| Path | Lines | Purpose |
|---|---|---|
| `substrate/foundation/__init__.py` | 1 | Foundation — substrate laws, identity, perspective. |
| `substrate/foundation/identity.py` | 58 | Identity continuity schema — maintains coherent self across time and context switches. |
| `substrate/foundation/laws.py` | 33 | Substrate laws — re-exports from substrate.ontology.laws. |
| `substrate/foundation/perspective.py` | 64 | Perspective schema — the lens through which the substrate interprets signals. |

## substrate/governance/ (20 files)

| Path | Lines | Purpose |
|---|---|---|
| `substrate/governance/README.md` | 26 | governance/ |
| `substrate/governance/__init__.py` | 9 | UMH Governance — risk classification, authority, and policy enforcement. |
| `substrate/governance/accountability/__init__.py` | 0 | package marker (empty) |
| `substrate/governance/accountability/accountability.py` | 320 | AccountabilityEngine — holds the founder to their word. |
| `substrate/governance/authority.py` | 27 | Authority levels — what the system can do without human intervention. |
| `substrate/governance/policy/__init__.py` | 0 | package marker (empty) |
| `substrate/governance/policy/authority_engine.py` | 267 | Authority engine — maps actions to RiskClass tiers and enforces approval authority per risk level |
| `substrate/governance/policy/authority_tier.py` | 49 | Authority tier constants and validation for ingestion sources. |
| `substrate/governance/policy/confidentiality.py` | 114 | Confidentiality Protocol — handles sensitive |
| `substrate/governance/policy/execution_authority_engine_v1.py` | 724 | Execution Authority Engine v1 for the UMH substrate layer. |
| `substrate/governance/policy_engine.py` | 183 | Policy engine — evaluates risk class + context to produce governance verdicts. |
| `substrate/governance/principles/__init__.py` | 0 | package marker (empty) |
| `substrate/governance/principles/principle_engine.py` | 519 | PrincipleEngine — injects quality standards into every AI decision. |
| `substrate/governance/quality/__init__.py` | 0 | package marker (empty) |
| `substrate/governance/quality/quality_gate.py` | 515 | QualityTransformationGate — every output passes through the four values. |
| `substrate/governance/risk_classes.py` | 150 | Action risk categories — semantic classification of side-effect types. |
| `substrate/governance/security.py` | 219 | Security hardening — input validation, rate limiting, audit logging. |
| `substrate/governance/validation/__init__.py` | 0 | package marker (empty) |
| `substrate/governance/validation/completeness_engine.py` | 287 | Completeness Engine — 13-slot validation for plans, workflows, and compositions. |
| `substrate/governance/validation/output_validator.py` | 314 | OutputValidator — EOS applies its own principles to its own outputs. |

## substrate/integrations/ (5 files)

| Path | Lines | Purpose |
|---|---|---|
| `substrate/integrations/__init__.py` | 9 | Substrate integration infrastructure — capability bridge, CORS, health, product connections. |
| `substrate/integrations/bridge.py` | 91 | UMH Bridge — connects UMH model routing to runtime/model_router.py. |
| `substrate/integrations/cors.py` | 44 | CORS configuration for UMH API. |
| `substrate/integrations/health.py` | 81 | Health aggregator — dashboard endpoint combining all service health signals. |
| `substrate/integrations/product_connections.py` | 205 | SaaS product connection manager — unified API for EOS, CreatorOS, LYFEOS. |

## substrate/intelligence/ (4 files)

| Path | Lines | Purpose |
|---|---|---|
| `substrate/intelligence/__init__.py` | 0 | package marker (empty) |
| `substrate/intelligence/finetune_harness.py` | 450 | Fine-tuning harness — scaffolds LoRA fine-tuning for self-hosted models. |
| `substrate/intelligence/runtime.py` | 439 | Proprietary Intelligence Runtime — the system's learned intelligence. |
| `substrate/intelligence/training_extractor.py` | 242 | Training data extraction from UMH execution traces. |

## substrate/memory/ (7 files)

| Path | Lines | Purpose |
|---|---|---|
| `substrate/memory/__init__.py` | 22 | Memory candidate staging, promotion, auto-reconciliation, bridging, and watching. |
| `substrate/memory/auto_reconciler.py` | 171 | AutoReconciler — closes the gap between promoted memories and canonical store. |
| `substrate/memory/candidate_generator.py` | 176 | MemoryCandidateGenerator — stages memory candidates from completed traces. |
| `substrate/memory/canonical_write.py` | 220 | CanonicalWritePath -- single facade for organism-loop memory writes. |
| `substrate/memory/claude_bridge.py` | 209 | Claude Bridge — syncs Claude Code memory files to substrate memory candidates. |
| `substrate/memory/promoter.py` | 254 | MemoryPromoter — evaluates candidates for promotion to durable storage. |
| `substrate/memory/watcher.py` | 337 | Memory Watcher — substrate-level filesystem watcher for agent memory directories. |

## substrate/meta_ide/ (18 files)

| Path | Lines | Purpose |
|---|---|---|
| `substrate/meta_ide/__init__.py` | 131 | Meta IDE — engineering reality awareness, planning, and proof loop. |
| `substrate/meta_ide/browser_evidence_collector.py` | 695 | Browser Evidence Collector — runs on executor nodes to collect verification evidence. |
| `substrate/meta_ide/browser_verification_gate.py` | 526 | Browser Verification Gate — blocking validation for UI-bearing work. |
| `substrate/meta_ide/engineering_execution.py` | 252 | Engineering Execution Contracts — governed execution session types. |
| `substrate/meta_ide/engineering_intent.py` | 198 | Engineering Intent Contract — types for autonomous engineering planning. |
| `substrate/meta_ide/engineering_planner.py` | 321 | Engineering Planner — deterministic planning from high-level intent. |
| `substrate/meta_ide/engineering_session_coordinator.py` | 860 | Engineering Session Coordinator — governed execution orchestration. |
| `substrate/meta_ide/engineering_work_generator.py` | 118 | Engineering Work Generator — bridge from plans to governed work packets. |
| `substrate/meta_ide/repository_model.py` | 278 | Repository reality model — read-only git awareness. |
| `substrate/meta_ide/review_package_builder.py` | 234 | Review Package Builder — deterministic proof assembly. |
| `substrate/meta_ide/roadmap_gap_engine.py` | 247 | Roadmap Gap Engine — detects gaps and recommends engineering work. |
| `substrate/meta_ide/roadmap_intelligence.py` | 218 | Roadmap intelligence — phase and planning awareness. |
| `substrate/meta_ide/shared_planner.py` | 30 | Shared EngineeringPlanner singleton for all cockpit route modules. |
| `substrate/meta_ide/workspace_intelligence.py` | 251 | Workspace intelligence — engineering-state awareness. |
| `substrate/meta_ide/workspace_observation.py` | 320 | Workspace Observation — live engineering runtime observation. |
| `substrate/meta_ide/workspace_registry.py` | 157 | Workspace Registry — single source of truth for workspace topology. |
| `substrate/meta_ide/workspace_runtime_graph.py` | 204 | Workspace Runtime Graph — canonical workspace topology models. |
| `substrate/meta_ide/workspace_topology_engine.py` | 271 | Workspace Topology Engine — live workspace topology with health. |

## substrate/observability/ (5 files)

| Path | Lines | Purpose |
|---|---|---|
| `substrate/observability/__init__.py` | 8 | Observability — trace, proof, outcome classification, and error recording. |
| `substrate/observability/error_recorder.py` | 57 | Canonical fix-forever error recorder. |
| `substrate/observability/jsonl_rotation.py` | 63 | JSONL rotation utility. |
| `substrate/observability/outcome_classifier.py` | 122 | OutcomeClassifier — classifies execution results into outcome categories. |
| `substrate/observability/trace_store.py` | 235 | TraceStore — append-only JSONL trace persistence. |

## substrate/ontology/ (8 files)

| Path | Lines | Purpose |
|---|---|---|
| `substrate/ontology/__init__.py` | 0 | package marker (empty) |
| `substrate/ontology/domains/__init__.py` | 17 | Domain bridges — re-exports from substrate.understanding.domains. |
| `substrate/ontology/domains/contract.py` | 12 | Domain bridge contract — re-exports from substrate.understanding.domains.contract. |
| `substrate/ontology/domains/creator.py` | 8 | Creator domain bridge — re-exports from substrate.understanding.domains.creator. |
| `substrate/ontology/domains/life.py` | 8 | Life domain bridge — re-exports from substrate.understanding.domains.life. |
| `substrate/ontology/laws.py` | 199 | Governing laws — enacted constraints that govern UMH like physics governs reality. |
| `substrate/ontology/primitives.py` | 25 | Ontology primitives — the computational physics of UMH. |
| `substrate/ontology/relationships.py` | 7 | Typed relationship edges between ontology observations. |

## substrate/operator/ (19 files)

| Path | Lines | Purpose |
|---|---|---|
| `substrate/operator/__init__.py` | 74 | UMH Operator — unified intent classification and routing layer. |
| `substrate/operator/continuity_engine.py` | 500 | Continuity Engine — operator presence and continuity aggregation. |
| `substrate/operator/device_continuity.py` | 128 | Device Continuity — per-device presence state tracking. |
| `substrate/operator/intent_receipt.py` | 146 | Unified intent receipt — canonical audit trail for every operator interaction. |
| `substrate/operator/intent_router.py` | 249 | Intent Router — deterministic-first classification of operator intent. |
| `substrate/operator/intent_runtime.py` | 589 | Intent Runtime — canonical intent preservation for operator continuity. |
| `substrate/operator/operator_attention_engine.py` | 320 | Operator Attention Engine — deterministic ranked priorities. |
| `substrate/operator/operator_context.py` | 204 | Operator Context Models — types for the operator home surface. |
| `substrate/operator/operator_context_engine.py` | 520 | Operator Context Engine — aggregation façade for operator home. |
| `substrate/operator/operator_presence.py` | 207 | Operator Presence Models — types for presence and continuity tracking. |
| `substrate/operator/operator_snapshot_runtime.py` | 488 | Operator Snapshot Runtime — answers the 5 operator questions. |
| `substrate/operator/presence_timeline.py` | 184 | Presence Timeline — operator presence transition tracking. |
| `substrate/operator/repository_context_resolver.py` | 107 | UMH Repository Context Resolver — maps workspace state to repo context. |
| `substrate/operator/screen_awareness.py` | 291 | UMH Screen Awareness — types for operator visual workspace context. |
| `substrate/operator/screen_context_providers.py` | 296 | UMH Screen Context Providers — three modes of screen awareness. |
| `substrate/operator/screen_observation_engine.py` | 272 | UMH Screen Observation Engine — node-role-aware screen context aggregation. |
| `substrate/operator/voice_query_engine.py` | 952 | Voice Query Engine — context-grounded query resolution. |
| `substrate/operator/workstation_session_runtime.py` | 412 | Workstation Session Runtime — operator leave/return with full context restore. |
| `substrate/operator/workstation_translator.py` | 210 | UMH Workstation Translator — Beast payload → canonical ScreenSnapshot. |

## substrate/organism/ (389 files)

| Path | Lines | Purpose |
|---|---|---|
| `substrate/organism/__init__.py` | 71 | UMH Organism — distributed orchestration substrate. |
| `substrate/organism/action_bridge.py` | 463 | Action Bridge — governed composition of catalog, observation, and execution. |
| `substrate/organism/action_catalog.py` | 308 | Action Catalog — data-driven registry of governed operator actions. |
| `substrate/organism/action_envelope.py` | 172 | ActionEnvelope — canonical executable object for ALL organism mutations. |
| `substrate/organism/action_voice_contract.py` | 80 | Voice/Intent Action Contract — interface between intent sources and ActionBridge. |
| `substrate/organism/advisor.py` | 815 | Advisor cell — the top-level orchestrator of the organism. |
| `substrate/organism/advisor_conversation.py` | 2,065 | Conversational advisor — multi-turn conversation with intent routing. |
| `substrate/organism/advisor_hierarchy.py` | 409 | Advisor Hierarchy — governed recursive advisory orchestration. |
| `substrate/organism/advisor_reconciliation.py` | 227 | Operator Reconciliation Integration — detects reconciliation intent in operator input. |
| `substrate/organism/agent_capability_model.py` | 281 | Agent Capability Model — track agent reliability per capability. |
| `substrate/organism/agent_execution_runner.py` | 637 | Agent Execution Runner — invokes coding agents inside governed sandboxes. |
| `substrate/organism/agent_fleet_runtime.py` | 589 | Agent Fleet Runtime — unified agent coordination layer. |
| `substrate/organism/agent_registry.py` | 261 | Agent Registry — agent types, capabilities, permissions, and routing. |
| `substrate/organism/agent_runtime.py` | 186 | Agent base runtime — the foundational behavior of every agent in the society. |
| `substrate/organism/agents.py` | 59 | Concrete agent cells — Researcher, Builder, AutoResearch. |
| `substrate/organism/allocation_loop.py` | 151 | Governed runtime allocation loop — continuous leverage allocator. |
| `substrate/organism/approval_authority.py` | 483 | Canonical approval authority (WP-P1-007). |
| `substrate/organism/approval_gate.py` | 378 | Operator Approval Gate — requires explicit approval before sandbox execution. |
| `substrate/organism/approval_store.py` | 133 | Approval store — JSONL persistence for governance-blocked signals. |
| `substrate/organism/artifact_registry.py` | 209 | Artifact Registry — indexes produced outputs across UMH. |
| `substrate/organism/assisted_executor.py` | 502 | Assisted Executor — governed execution of approved maintenance actions. |
| `substrate/organism/assumption_tracking_runtime.py` | 188 | Assumption Tracking Runtime — governed assumption records for UMH. |
| `substrate/organism/async_coordinator.py` | 261 | Async coordinator execution — event-driven objective lifecycle. |
| `substrate/organism/audits/__init__.py` | 0 | package marker (empty) |
| `substrate/organism/audits/context_capacity.py` | 181 | Audit — Context Capacity. |
| `substrate/organism/audits/empire_readiness.py` | 196 | Audit — Empire Readiness. |
| `substrate/organism/audits/model_correspondence.py` | 164 | Model Correspondence Audit — predicted state vs observed reality. |
| `substrate/organism/audits/operational_awareness.py` | 87 | Audit — Operational Awareness. |
| `substrate/organism/audits/organism_awareness.py` | 129 | Audit — Organism Self-Awareness. |
| `substrate/organism/audits/source_truth.py` | 138 | Audit — Source of Truth (Production Lineage). |
| `substrate/organism/automation_pipeline.py` | 247 | Automation Candidate Pipeline — promote repeated interventions to automation. |
| `substrate/organism/autonomous_action_gateway.py` | 422 | Autonomous Action Gateway — structural enforcement of spine-routed mutation. |
| `substrate/organism/autonomous_cadence.py` | 325 | Autonomous Cadence — scheduled autonomous improvement discovery. |
| `substrate/organism/autonomous_improvement_lane.py` | 908 | Autonomous Improvement Lane — bounded autonomous LOW-risk self-improvement. |
| `substrate/organism/autonomous_pr_factory.py` | 866 | Autonomous PR Factory — converts eligible improvements into isolated PRs. |
| `substrate/organism/autonomous_tick.py` | 285 | Autonomous tick engine — continuous organism metabolism heartbeat. |
| `substrate/organism/benchmark_harness.py` | 416 | Benchmark Harness — measures and compares Pipeline A (legacy) vs Pipeline B (governed). |
| `substrate/organism/benchmarks/__init__.py` | 0 | package marker (empty) |
| `substrate/organism/benchmarks/autonomous_execution.py` | 85 | Autonomous Execution Benchmark — session depth, recovery, and independence. |
| `substrate/organism/benchmarks/capability_reuse.py` | 233 | Benchmark 4 — Capability Reuse (Dual-Track). |
| `substrate/organism/benchmarks/company_ops.py` | 222 | Company Operations Scorer — Benchmark F for C33. |
| `substrate/organism/benchmarks/competitive.py` | 273 | Competitive benchmarking data layer — competitor profiles, market categories, and scoring. |
| `substrate/organism/benchmarks/composite_scorer.py` | 245 | Composite Scorer — aggregate 20 categories into competitive matrix. |
| `substrate/organism/benchmarks/compounding_proof.py` | 217 | Benchmark 7 — Compounding Proof (Integration). |
| `substrate/organism/benchmarks/efficiency.py` | 117 | Efficiency Benchmark — capability per dollar. |
| `substrate/organism/benchmarks/external_adapters.py` | 363 | External benchmark adapter layer — industry-standard benchmarks through UMH. |
| `substrate/organism/benchmarks/governance_quality.py` | 218 | Governance Quality Scorer — Benchmark D for C33. |
| `substrate/organism/benchmarks/harness_scorer.py` | 793 | C29 Harness Superiority — Scoring engine. |
| `substrate/organism/benchmarks/harness_superiority.py` | 1,141 | C29 Harness Superiority — data model, task registry, result store. |
| `substrate/organism/benchmarks/human_amplification.py` | 131 | Human Amplification Benchmark — does the operator become more capable? |
| `substrate/organism/benchmarks/mutation_equivalence.py` | 340 | Mutation Equivalence Scorer — Benchmark H for C33. |
| `substrate/organism/benchmarks/operator_compression.py` | 264 | Benchmark 5 — Operator Compression. |
| `substrate/organism/benchmarks/orchestration_quality.py` | 221 | Orchestration Quality Scorer — Benchmark C for C33. |
| `substrate/organism/benchmarks/outcome_accuracy.py` | 87 | Outcome Accuracy Benchmark — did completed work achieve original intent? |
| `substrate/organism/benchmarks/production_outcome_quality.py` | 248 | Benchmark 6 — Production Outcome Quality. |
| `substrate/organism/benchmarks/production_quality.py` | 246 | Benchmark 2 — Production Quality. |
| `substrate/organism/benchmarks/production_velocity.py` | 146 | Benchmark 3 — Production Velocity. |
| `substrate/organism/benchmarks/projection_readiness.py` | 196 | Benchmark — Projection Readiness. |
| `substrate/organism/benchmarks/reality_correspondence.py` | 1,239 | Reality Correspondence Benchmark — 50 failure scenarios across 5 domains. |
| `substrate/organism/benchmarks/reality_recovery.py` | 585 | Benchmark 1 — Reality Recovery. |
| `substrate/organism/benchmarks/reliability.py` | 94 | Reliability Benchmark — consistency across repeated builds. |
| `substrate/organism/benchmarks/strategic_compression.py` | 91 | Strategic Compression Benchmark — high-level intent to executable reality. |
| `substrate/organism/benchmarks/surface_switching.py` | 234 | Surface Switching Cost Tracker — measures continuity across UMH surfaces. |
| `substrate/organism/bottleneck_engine.py` | 484 | Bottleneck Detection Engine — organism operational self-optimization. |
| `substrate/organism/candidate_supply_engine.py` | 614 | Candidate Supply Engine — discovers improvement candidates from real organism sources. |
| `substrate/organism/canonical_runtime.py` | 66 | Canonical operation runtime — the single declared mutation-submission entry. |
| `substrate/organism/canonical_update.py` | 191 | Canonical Update Proposal — proposed changes to canonical truth. |
| `substrate/organism/capability_compounding_runtime.py` | 584 | Capability Compounding Runtime — Campaign 22.4 |
| `substrate/organism/capability_evolution_engine.py` | 523 | Capability Evolution Engine — Campaign 12.2 |
| `substrate/organism/capability_gap_engine.py` | 285 | Capability Gap Engine — detect missing or immature capabilities for goals. |
| `substrate/organism/capability_graph_engine.py` | 360 | Capability Graph Engine — explicit dependency/composition edges between capabilities. |
| `substrate/organism/capability_portfolio_runtime.py` | 254 | Capability Portfolio Runtime — portfolio-level health and compounding metrics. |
| `substrate/organism/capability_runtime.py` | 472 | Capability Runtime — emergent capability tracking and maturity lifecycle. |
| `substrate/organism/capability_validation_runtime.py` | 505 | Capability Validation Runtime — benchmark storage, reporting, and freshness tracking. |
| `substrate/organism/change_event.py` | 370 | Change Event — state change model for propagation planning. |
| `substrate/organism/changeset_manifest.py` | 295 | Changeset Manifest — evidence record for every autonomous branch/PR. |
| `substrate/organism/claude_code_runtime_adapter.py` | 179 | Claude Code PTY runtime adapter — skeleton with truthful availability. |
| `substrate/organism/coherence_propagation.py` | 534 | Coherence Propagation Engine — parallel dependent-system updates on verified change. |
| `substrate/organism/command_runtime.py` | 1,395 | Command Runtime — operator intent normalization/classification layer. |
| `substrate/organism/composition_engine.py` | 465 | Composition Engine — deterministic intent → plan from observed capabilities. |
| `substrate/organism/compounding_engine.py` | 583 | Capability Compounding Engine — turn internal learning into leverage. |
| `substrate/organism/compute_fabric_runtime.py` | 454 | Compute Fabric Runtime — unified compute body map. |
| `substrate/organism/context_diagnostic.py` | 227 | Context Diagnostic — models for diagnostic reports on context state. |
| `substrate/organism/context_ingestion_engine.py` | 450 | Context Ingestion Engine — ingest local/system context sources. |
| `substrate/organism/context_resolution.py` | 556 | Context Resolution Engine — "the system already knows" layer. |
| `substrate/organism/continuity_runtime.py` | 1,353 | Continuity Runtime — operational continuity engine for UMH. |
| `substrate/organism/continuous_qualification.py` | 231 | Continuous Qualification — daemon tick stage for live ORL measurement. |
| `substrate/organism/contradiction_engine.py` | 396 | Contradiction Engine — detect mismatches between declared and observed reality. |
| `substrate/organism/coordinator.py` | 618 | OrganismCoordinator — hierarchical task decomposition and runtime assignment. |
| `substrate/organism/correspondence_scheduler.py` | 229 | Correspondence Scheduler — periodic drift detection for projections. |
| `substrate/organism/council.py` | 285 | Council — multi-perspective advisory layer for the advisor. |
| `substrate/organism/cross_source_reconciler.py` | 345 | Cross-Source Reconciler — detect relationships across fragmented sources. |
| `substrate/organism/daemon.py` | 1,136 | Organism daemon — manages agent lifecycle within the control plane. |
| `substrate/organism/daily_driver_log.py` | 112 | Daily Driver Log — records unhandled failures during real operation. |
| `substrate/organism/decision_impact_engine.py` | 265 | Decision Impact Engine — blast radius analysis for strategic decisions. |
| `substrate/organism/decision_lineage_engine.py` | 363 | Decision Lineage Engine — causal chain traversal for strategic decisions. |
| `substrate/organism/decision_registry.py` | 309 | Decision Registry — first-class strategic decision records for UMH. |
| `substrate/organism/decision_validity_engine.py` | 314 | Decision Validity Engine — evaluates whether decisions still make sense. |
| `substrate/organism/delegation_followup.py` | 228 | Automated delegation follow-up — checks overdue delegations and acts. |
| `substrate/organism/delegation_readiness_runtime.py` | 515 | Delegation Readiness Runtime — pre-assignment feasibility + outcome prediction. |
| `substrate/organism/delegation_runtime.py` | 883 | Delegation Runtime — intent classification, delegation proposals, mission lifecycle. |
| `substrate/organism/delegation_topology.py` | 202 | Delegation Topology Planner — chooses execution structure for a work packet. |
| `substrate/organism/dependency_graph.py` | 401 | Dependency Graph — subsystem dependency model for UMH. |
| `substrate/organism/deploy_verification_worker.py` | 529 | Deploy verification worker — no human should discover a white screen. |
| `substrate/organism/dev_session_tracker.py` | 219 | DevSessionTracker — wraps development sessions as governed spine executions. |
| `substrate/organism/development_session_bridge.py` | 353 | DevelopmentSessionBridge — makes coding agents governed organs of the organism. |
| `substrate/organism/device_awareness.py` | 221 | Device Awareness Runtime — deterministic device detection and capability routing. |
| `substrate/organism/device_capacity.py` | 111 | Device Capacity Model — per-device worker slots and backpressure. |
| `substrate/organism/device_provisioner.py` | 465 | Device Provisioner — multi-OS diagnosis + role-based provisioning. |
| `substrate/organism/device_registry_writer.py` | 210 | Device Registry Writer — atomic writes + cache invalidation. |
| `substrate/organism/device_role_registry.py` | 277 | Device role registry — tracks device roles and capabilities in the UMH organism. |
| `substrate/organism/dex_conversation.py` | 8 | Backward-compat shim — canonical module is advisor_conversation.py. |
| `substrate/organism/dex_reconciliation.py` | 4 | Backward-compat shim — canonical module is advisor_reconciliation.py. |
| `substrate/organism/diagnostic_engine.py` | 332 | Diagnostic Engine — analyze ingested context for canonical truth state. |
| `substrate/organism/distributed_runtime.py` | 236 | Distributed Runtime — facade composing all distributed runtime subsystems. |
| `substrate/organism/documentation_awareness_runtime.py` | 327 | Documentation Awareness Runtime — content-level metadata for docs. |
| `substrate/organism/domain_registry.py` | 359 | Domain Registry — first-class domain definitions for the Empire WorkPacket Engine. |
| `substrate/organism/drift_detection_engine.py` | 254 | Drift Detection Engine — unified drift synthesis. |
| `substrate/organism/embodiment_runtime.py` | 509 | Embodiment Runtime — natural language intent becomes governed work. |
| `substrate/organism/empire_router.py` | 421 | Empire Router — routes founder intent to domain-classified, governed WorkPackets. |
| `substrate/organism/environment_discovery.py` | 346 | Environment Discovery — device, filesystem, application, account inventory. |
| `substrate/organism/environment_graph.py` | 238 | Environment graph — continuously updated operational world-state. |
| `substrate/organism/environment_reconciler.py` | 185 | Environment reconciliation — continuous drift correction. |
| `substrate/organism/event_spine.py` | 292 | Unified organism event spine — canonical organism-level event transport. |
| `substrate/organism/execution_coordinator.py` | 1,191 | Execution Coordinator Runtime — canonical orchestration layer (Phase 13). |
| `substrate/organism/execution_economy.py` | 392 | Execution Economy — runtime cost/value tracking and leverage scoring. |
| `substrate/organism/execution_graph.py` | 431 | Execution Graph — evidence-grade lineage validation over existing execution infrastructure. |
| `substrate/organism/execution_journal.py` | 240 | ExecutionJournal — append-only execution ledger for all organism mutations. |
| `substrate/organism/execution_ledger.py` | 186 | Execution Ledger — canonical record of every execution request and outcome. |
| `substrate/organism/execution_lifecycle_runtime.py` | 422 | Execution Lifecycle Runtime — Campaign 16.2. |
| `substrate/organism/execution_modes.py` | 282 | Execution Modes — governed transition from observation to action. |
| `substrate/organism/executive_brief_runtime.py` | 555 | Executive Brief Runtime — structured operator briefing synthesis. |
| `substrate/organism/executive_portfolio_runtime.py` | 664 | C14.2 — Executive Portfolio Runtime. |
| `substrate/organism/executor_runtime.py` | 1,513 | Executor Runtime — canonical execution contract layer (Phase 14). |
| `substrate/organism/executors/__init__.py` | 9 | Executor implementations for the UMH Executor Runtime. |
| `substrate/organism/executors/agent_executor.py` | 828 | AgentExecutor — first governed LLM/Claude Code executor (Phase 17A). |
| `substrate/organism/executors/approval_intercept.py` | 682 | Approval Intercepts — runtime human-in-the-loop governance for executors. |
| `substrate/organism/executors/execution_telemetry.py` | 403 | Execution Telemetry — live event pipeline for executor lifecycle. |
| `substrate/organism/executors/workstation_executor.py` | 785 | WorkstationExecutor — first production ExecutorContract implementation. |
| `substrate/organism/goal_alignment_engine.py` | 214 | Goal Alignment Engine — ensure work supports goals. |
| `substrate/organism/goal_drift_engine.py` | 264 | Goal Drift Engine — detect movement away from objectives. |
| `substrate/organism/goal_hierarchy_engine.py` | 226 | Goal Hierarchy Engine — structural operations on the goal tree. |
| `substrate/organism/governance_runtime.py` | 686 | C15.0 — Governance Runtime. |
| `substrate/organism/governed_execution_runtime.py` | 665 | Governed Execution Runtime — Campaign 16.0. |
| `substrate/organism/governed_spine.py` | 889 | GovernedExecutionSpine — THE single mutation gateway in the organism. |
| `substrate/organism/governed_work_runtime.py` | 589 | Governed Work Runtime — work-lifecycle adapter onto the canonical runtime. |
| `substrate/organism/grounded_handlers.py` | 543 | Grounded status handlers — deterministic answers backed by real data. |
| `substrate/organism/grounding_registry.py` | 625 | Grounding registry — source data requirements for deterministic status answers. |
| `substrate/organism/handoff.py` | 226 | Agent handoff protocol — structured agent-to-agent task transfer. |
| `substrate/organism/homeostasis.py` | 566 | Homeostasis — the organism's immune/self-regulation system. |
| `substrate/organism/impact_analyzer.py` | 323 | Impact Analyzer — computes change impact across the propagation graph. |
| `substrate/organism/infrastructure_runtime.py` | 392 | Infrastructure Runtime — register and track system & institutional infrastructure. |
| `substrate/organism/ingestion_job.py` | 259 | Ingestion Job — tracks context ingestion work units. |
| `substrate/organism/institutional_memory_runtime.py` | 557 | C15.2 — Institutional Memory Runtime. |
| `substrate/organism/intent_classifier.py` | 324 | Intent Classifier — converts raw user intent into structured classification. |
| `substrate/organism/knowledge_awareness_runtime.py` | 270 | Knowledge Awareness Runtime — meaning, not just documents. |
| `substrate/organism/knowledge_model_registry.py` | 167 | Knowledge Model Registry — system knowledge containers. |
| `substrate/organism/learning_extraction_runtime.py` | 690 | Learning Extraction Runtime — Campaign 12.0 |
| `substrate/organism/learning_portfolio_runtime.py` | 562 | Learning Portfolio Runtime — Campaign 12.3 |
| `substrate/organism/leverage_assimilation.py` | 618 | External Leverage Assimilation — ingest, classify, and operationalize |
| `substrate/organism/leverage_engine.py` | 298 | Leverage Engine — determines highest-impact actions. |
| `substrate/organism/leverage_metrics.py` | 262 | Operational Leverage Metrics — measures actual organism value. |
| `substrate/organism/maintenance_loop.py` | 313 | Autonomous Maintenance Loop — OBSERVE-mode infrastructure health cycle. |
| `substrate/organism/memory_promotion.py` | 514 | Memory Promotion Pipeline — governed promotion from instance to canonical memory. |
| `substrate/organism/mesh_reconciler.py` | 232 | Mesh node reconciliation — syncs RuntimeGraph with live mesh relay. |
| `substrate/organism/meta_ide_runtime.py` | 538 | Meta IDE Runtime — unified development surface. |
| `substrate/organism/mission.py` | 256 | Mission — bridge between user conversation and organism execution. |
| `substrate/organism/mutation_catalog.py` | 109 | MutationCatalog — maps HTTP endpoints to MutationSpec names. |
| `substrate/organism/mutation_registry.py` | 912 | MutationRegistry — canonical registry of executable mutation types. |
| `substrate/organism/mutation_router.py` | 378 | MutationRouter — canonical choke point for all organism state mutations. |
| `substrate/organism/next_action_engine.py` | 275 | Next Action Engine — evidence-based action recommender. |
| `substrate/organism/objective_physics.py` | 320 | Objective Physics — causal execution dynamics. |
| `substrate/organism/objective_queue.py` | 231 | Continuous objective queue — intake front door for OrganismCoordinator. |
| `substrate/organism/observability.py` | 329 | Organism Observability — unified dashboard snapshot. |
| `substrate/organism/operating_loop_coherence_runtime.py` | 475 | Operating Loop Coherence Runtime — aggregation, reporting, coherence synthesis. |
| `substrate/organism/operational_truth.py` | 352 | OperationalTruthSnapshot — scoreboard for UMH operational reality. |
| `substrate/organism/operationalization_runtime.py` | 399 | Operationalization Runtime — link capabilities to reusable artifacts. |
| `substrate/organism/operator_acceptance.py` | 298 | Operator acceptance run model — end-to-end acceptance test tracking. |
| `substrate/organism/operator_acceptance_mode.py` | 378 | Operator acceptance mode — standard multi-runtime vs deterministic-only vs blocked. |
| `substrate/organism/operator_acceptance_scenarios.py` | 248 | Operator acceptance scenarios — predefined end-to-end test scenarios. |
| `substrate/organism/operator_compression.py` | 195 | Operator Compression — reduce human operational burden. |
| `substrate/organism/operator_escape_tracker.py` | 163 | Operator Escape Tracker — records exits from UMH organism. |
| `substrate/organism/operator_loop_coordinator.py` | 785 | Operator loop coordinator — orchestrates the end-to-end acceptance loop. |
| `substrate/organism/operator_loop_runtime.py` | 391 | Operator Loop Runtime — the Jarvis Runtime. |
| `substrate/organism/operator_migration_runtime.py` | 464 | Operator Migration Runtime — track and close external-loop dependencies. |
| `substrate/organism/operator_readiness_gate.py` | 306 | OperatorReadinessGate — Phase 13.4 readiness assessment. |
| `substrate/organism/operator_response.py` | 217 | Operator Response — structured response contract for the orchestrator kernel. |
| `substrate/organism/operator_session.py` | 349 | Operator Session — conversational state for operator-orchestrator interaction. |
| `substrate/organism/orchestration_loop.py` | 447 | Orchestration loop — persistent autonomous execution for the organism. |
| `substrate/organism/orchestrator_awareness_runtime.py` | 585 | Orchestrator Awareness Runtime — synthesized reality model for the orchestrator. |
| `substrate/organism/orchestrator_kernel.py` | 940 | Orchestrator Kernel — central intelligence routing for operator interaction. |
| `substrate/organism/organism_coordination_engine.py` | 497 | C15.1 — Organism Coordination Engine. |
| `substrate/organism/organism_loop.py` | 564 | OrganismLoopEngine -- convergence coordinator for organism execution. |
| `substrate/organism/organism_portfolio_runtime.py` | 422 | C15.3 — Organism Portfolio Runtime. |
| `substrate/organism/organism_state_runtime.py` | 282 | Organism State Runtime — Campaign 16.1. |
| `substrate/organism/outcome_learning.py` | 624 | Outcome Learning Loop — learn from execution outcomes. |
| `substrate/organism/outcome_pattern_engine.py` | 748 | Outcome Pattern Engine — Campaign 12.1 |
| `substrate/organism/outcome_tracking_runtime.py` | 252 | Outcome Tracking Runtime — measure progress toward goals. |
| `substrate/organism/outcome_verification.py` | 449 | Outcome verification engine — replaces 'Task Complete' with 'Outcome Verified'. |
| `substrate/organism/packet_router.py` | 286 | Packet Router — capability-first work routing. |
| `substrate/organism/parallel.py` | 212 | Parallel agent execution — run multiple agents concurrently. |
| `substrate/organism/permission_dialogue.py` | 394 | Socratic Permission Engine — ask before expanding context access. |
| `substrate/organism/plan_execution_adapter.py` | 715 | Plan Execution Adapter — bridges CompositionPlan to GovernedExecutionSpine. |
| `substrate/organism/prediction_portfolio_runtime.py` | 523 | Prediction Portfolio Runtime — Campaign 13.2 |
| `substrate/organism/presence_runtime.py` | 973 | Presence Runtime — operator presence awareness for UMH. |
| `substrate/organism/priority_engine.py` | 238 | Priority Engine — deterministic priority synthesis. |
| `substrate/organism/product_factory_runtime.py` | 787 | C22.5 — Product Factory Runtime. |
| `substrate/organism/production_merge_verifier.py` | 611 | Production Merge Verifier — confirms sandboxed PR became production truth. |
| `substrate/organism/production_ops_runtime.py` | 575 | Production Operations Runtime — Campaign 22.0. |
| `substrate/organism/production_planning_runtime.py` | 645 | C22.1 — Production Planning Runtime. |
| `substrate/organism/production_review_runtime.py` | 847 | C22.3 — Production Review Runtime. |
| `substrate/organism/production_truth_delta.py` | 444 | Production Truth Delta — what actually changed in production after merge. |
| `substrate/organism/production_workforce_runtime.py` | 702 | Production Workforce Runtime — Campaign 22.2. |
| `substrate/organism/profile_runtime.py` | 1,490 | Profile Runtime — canonical authority for operator work identity and system modes. |
| `substrate/organism/project_registry.py` | 161 | Project Registry — first-class project entities for UMH. |
| `substrate/organism/projection_certification.py` | 435 | Projection certification framework — graduated L0-L5 certification. |
| `substrate/organism/projection_engine.py` | 1,449 | Projection Engine — predictive world-model layer for UMH. |
| `substrate/organism/projection_integration_runtime.py` | 580 | Projection Integration Runtime — audit/mapping layer over projections. |
| `substrate/organism/projection_port.py` | 165 | Projection-agnostic organism state-broadcast port. |
| `substrate/organism/projection_readiness_gate.py` | 134 | Projection Readiness Gate — blocks feature build until source reconciliation is sufficient. |
| `substrate/organism/projection_reconciliation_engine.py` | 323 | Projection Reconciliation Engine — diagnoses divergence across projection sources. |
| `substrate/organism/projection_source_registry.py` | 252 | Projection Source Registry — tracks sources per projection for reconciliation. |
| `substrate/organism/promotion_threshold_policy.py` | 271 | Promotion Threshold Policy — governs cadence mode transitions. |
| `substrate/organism/proof_runtime.py` | 309 | Proof Runtime — complete proof packages per execution. |
| `substrate/organism/proof_store.py` | 179 | Proof Store — JSONL persistence for proof packages. |
| `substrate/organism/propagation_executor.py` | 239 | Propagation Executor — executes propagation plans in dry-run or governed mode. |
| `substrate/organism/propagation_graph.py` | 433 | Propagation Graph — dependency-aware change propagation model. |
| `substrate/organism/propagation_graph_builder.py` | 532 | Propagation Graph Builder — extracts nodes and edges from real system state. |
| `substrate/organism/propagation_planner.py` | 196 | Propagation Planner — creates wave-based propagation plans. |
| `substrate/organism/propagation_wiring.py` | 296 | Propagation wiring — registers all propagation targets with the engine. |
| `substrate/organism/protocols.py` | 75 | Organism protocols — typed contracts for the agent society. |
| `substrate/organism/qualification_harness.py` | 1,569 | Organism Qualification Harness. |
| `substrate/organism/readiness_model.py` | 419 | System Readiness Model — 6-dimension readiness assessment. |
| `substrate/organism/reality_graph.py` | 800 | Reality Graph — canonical operator-world graph for UMH. |
| `substrate/organism/recommendation_engine.py` | 240 | Recommendation Engine — unified action recommendation synthesis. |
| `substrate/organism/reconciliation_engine.py` | 265 | Reconciliation Engine — structured context reconciliation sessions. |
| `substrate/organism/reconciliation_session.py` | 234 | Reconciliation Session — structured operator-AI context alignment. |
| `substrate/organism/recursion_governance.py` | 404 | Recursion Governance — bounded recursive execution control. |
| `substrate/organism/reliability_signals.py` | 464 | Reliability Signal Model — normalizes production-backed signals for cadence ranking. |
| `substrate/organism/reliability_weighted_ranker.py` | 300 | Reliability-Weighted Ranker — deterministic candidate ranking using production signals. |
| `substrate/organism/report_dispatcher.py` | 245 | Report dispatcher — sends task completion reports to Discord + cockpit chat. |
| `substrate/organism/repository_awareness_runtime.py` | 306 | Repository Awareness Runtime — file-level depth for repositories. |
| `substrate/organism/resource_allocation_runtime.py` | 688 | C14.0 — Resource Allocation Runtime. |
| `substrate/organism/risk_engine.py` | 242 | Risk Engine — unified risk register synthesis. |
| `substrate/organism/roadmap_engine.py` | 164 | Roadmap Engine — phase linkage model for self-build queue. |
| `substrate/organism/role_contracts.py` | 243 | Role Contracts + Capability Profiles — template-based role definitions. |
| `substrate/organism/runtime_adapter.py` | 120 | Runtime adapter interface — abstract contract for execution surfaces. |
| `substrate/organism/runtime_adapters.py` | 893 | Concrete RuntimeAdapter implementations for UMH runtimes. |
| `substrate/organism/runtime_awareness_runtime.py` | 213 | Runtime Awareness Runtime — unified view of active system state. |
| `substrate/organism/runtime_fleet.py` | 359 | Runtime fleet model — tracks available runtime providers and selection decisions. |
| `substrate/organism/runtime_graph.py` | 409 | RuntimeGraph — canonical runtime registry with dynamic availability. |
| `substrate/organism/runtime_handoff.py` | 208 | Runtime handoff — bridges Work Packets to runtime sessions. |
| `substrate/organism/runtime_manager.py` | 386 | Runtime manager — orchestrates governed runtime session lifecycle. |
| `substrate/organism/runtime_session.py` | 262 | Runtime session model — governed execution surface for workcell runtimes. |
| `substrate/organism/runtime_state_registry.py` | 587 | Runtime State Registry — live environment awareness for the workstation. |
| `substrate/organism/runtime_supervisor.py` | 429 | RuntimeSupervisor — persistent runtime lifecycle management. |
| `substrate/organism/sandbox_orchestrator.py` | 216 | Sandbox Orchestrator — ties approval gate to PR factory execution. |
| `substrate/organism/scenario_intelligence_engine.py` | 659 | Scenario Intelligence Engine — Campaign 13.1 |
| `substrate/organism/self_build_queue.py` | 707 | Self-Build Engineering Queue — canonical work item model and queue engine. |
| `substrate/organism/self_maintenance_bridge.py` | 95 | Self-Regulation Bridge — wires degradation detection to work packet creation. |
| `substrate/organism/self_model_predictor.py` | 542 | PredictiveSelfModel — the organism's statistical self-prediction engine. |
| `substrate/organism/self_use/__init__.py` | 71 | Self-use certification — C27 Daily Driver Readiness. |
| `substrate/organism/self_use/certification_report.py` | 277 | Certification report — 4-gate pass/fail with coherence override. |
| `substrate/organism/self_use/gap_ledger.py` | 186 | Gap ledger — structured log of every friction point, missing capability, and failure. |
| `substrate/organism/self_use/meta_ide_audit.py` | 222 | Meta IDE functional audit — manual operator testing of every subsystem. |
| `substrate/organism/self_use/projection_delta.py` | 230 | Projection delta engine — desired vs implemented vs certified. |
| `substrate/organism/self_use/task_catalog.py` | 202 | Task catalog — load and manage C27 self-use certification tasks. |
| `substrate/organism/self_use/task_taxonomy.py` | 52 | Task taxonomy — domain classification for self-use certification. |
| `substrate/organism/service_dependency_graph.py` | 166 | Service Dependency Graph — canonical service dependency models. |
| `substrate/organism/service_dependency_registry.py` | 139 | Service Dependency Registry — canonical registry of service dependencies. |
| `substrate/organism/service_failure_engine.py` | 168 | Service Failure Engine — computes failure impact across service graph. |
| `substrate/organism/session_runtime.py` | 1,114 | Session Runtime — canonical session architecture for UMH. |
| `substrate/organism/shell_runtime_adapter.py` | 445 | Shell runtime adapter — safe subprocess execution surface. |
| `substrate/organism/slo_definitions.py` | 127 | Runtime SLO Definitions — concrete operational targets. |
| `substrate/organism/source_registry.py` | 231 | Source Registry — tracks all context sources available to UMH. |
| `substrate/organism/source_truth_linker.py` | 295 | Source Truth Linker — cross-domain edge builder for the Reality Graph. |
| `substrate/organism/source_truth_runtime.py` | 877 | Source Truth Runtime — full organizational lineage (Campaign 22.6 CORE). |
| `substrate/organism/spine_guard.py` | 240 | SpineGuard — enforcement layer for the single-spine mutation doctrine. |
| `substrate/organism/state_authority_graph.py` | 131 | State Authority Graph — canonical state domain authority models. |
| `substrate/organism/state_coherence_engine.py` | 174 | State Coherence Engine — detects state authority coherence across nodes. |
| `substrate/organism/state_registry.py` | 108 | State Registry — canonical registry of state domain authorities. |
| `substrate/organism/store.py` | 137 | Organism store — JSONL persistence for deliverables, messages, agent state. |
| `substrate/organism/strategic_context_runtime.py` | 513 | Strategic Context Runtime — unified executive synthesis facade. |
| `substrate/organism/strategic_gap_engine.py` | 977 | Strategic Gap Engine — compares current reality to target goals, produces gaps, |
| `substrate/organism/strategic_memory_engine.py` | 431 | Strategic Memory Engine — institutional memory with timeline and replay. |
| `substrate/organism/strategic_planning_engine.py` | 346 | Strategic Planning Engine — generate plans linking current reality to goals. |
| `substrate/organism/strategic_tick_loop.py` | 870 | Strategic Tick Loop — continuous governed awareness engine. |
| `substrate/organism/sync_policy.py` | 173 | External Sync Policy — governs how UMH relates to external tools. |
| `substrate/organism/system_identity.py` | 138 | Canonical UMH identity — single source of truth. |
| `substrate/organism/tailscale_discovery.py` | 322 | Tailscale auto-discovery tick — diffs tailscale peers vs device registry. |
| `substrate/organism/template_governance.py` | 337 | Template Governance — 9-dimension scoring engine for template cadence eligibility. |
| `substrate/organism/template_registry.py` | 936 | Template Registry — reusable executable structures from governed execution. |
| `substrate/organism/template_seeder.py` | 1,171 | Template Seeder — seeds evidence-backed execution templates to the runtime store. |
| `substrate/organism/tests/__init__.py` | 0 | package marker (empty) |
| `substrate/organism/tests/test_advisor.py` | 46 | Tests for advisor — interpret, decompose, delegate, synthesize. |
| `substrate/organism/tests/test_advisor_coordinator.py` | 158 | Tests for advisor → coordinator integration (Phase 2A). |
| `substrate/organism/tests/test_agent_runtime.py` | 78 | tests for agent base runtime — critique loop, deliverable production. |
| `substrate/organism/tests/test_allocation_loop.py` | 115 | Tests for the governed runtime allocation loop. |
| `substrate/organism/tests/test_approval_store.py` | 68 | tests for approval store — JSONL persistence for governance-blocked signals. |
| `substrate/organism/tests/test_assisted_executor.py` | 128 | Tests for the AssistedExecutor — Phase 5.9. |
| `substrate/organism/tests/test_async_coordinator.py` | 121 | Tests for async coordinator execution. |
| `substrate/organism/tests/test_automation_pipeline.py` | 132 | Tests for the AutomationPipeline — Phase 5.9. |
| `substrate/organism/tests/test_autonomous_tick.py` | 182 | Tests for the autonomous tick engine. |
| `substrate/organism/tests/test_bottleneck_engine.py` | 131 | Tests for BottleneckEngine. |
| `substrate/organism/tests/test_composition_engine.py` | 198 | Tests for composition engine. |
| `substrate/organism/tests/test_contradiction_engine.py` | 190 | Tests for contradiction engine. |
| `substrate/organism/tests/test_coordinator.py` | 241 | Tests for OrganismCoordinator — task decomposition, assignment, execution. |
| `substrate/organism/tests/test_daemon_approvals.py` | 67 | tests for daemon approval creation on governance rejection. |
| `substrate/organism/tests/test_dependency_graph.py` | 189 | Tests for organism dependency graph. |
| `substrate/organism/tests/test_development_session_bridge.py` | 241 | Tests for DevelopmentSessionBridge — governed coding agent integration. |
| `substrate/organism/tests/test_e2e.py` | 63 | End-to-end test — the vertical slice acceptance criterion. |
| `substrate/organism/tests/test_environment_graph.py` | 156 | Tests for EnvironmentGraph — operational topology. |
| `substrate/organism/tests/test_environment_reconciler.py` | 163 | Tests for EnvironmentReconciler — drift correction. |
| `substrate/organism/tests/test_event_spine.py` | 235 | Tests for the unified organism event spine. |
| `substrate/organism/tests/test_execution_modes.py` | 114 | Tests for ExecutionModeManager. |
| `substrate/organism/tests/test_leverage_assimilation.py` | 279 | Tests for leverage_assimilation — external framework ingestion and scoring. |
| `substrate/organism/tests/test_leverage_metrics.py` | 133 | Tests for LeverageMetrics engine. |
| `substrate/organism/tests/test_leverage_rebalance.py` | 52 | Tests for continuous leverage rebalancing. |
| `substrate/organism/tests/test_maintenance_loop.py` | 90 | Tests for the MaintenanceLoop — Phase 5.9. |
| `substrate/organism/tests/test_memory_promotion.py` | 302 | Tests for memory promotion pipeline. |
| `substrate/organism/tests/test_mission.py` | 242 | Tests for Mission — user conversation to organism execution bridge. |
| `substrate/organism/tests/test_objective_physics.py` | 138 | Tests for ObjectivePhysics engine. |
| `substrate/organism/tests/test_objective_queue.py` | 168 | Tests for the continuous objective queue. |
| `substrate/organism/tests/test_operational_intelligence.py` | 330 | Tests for Phase 7.0 Operational Intelligence engines. |
| `substrate/organism/tests/test_operator_compression.py` | 106 | Tests for OperatorCompression engine. |
| `substrate/organism/tests/test_orchestration_integration.py` | 480 | Integration tests for Phase 2 organism orchestration. |
| `substrate/organism/tests/test_orchestration_loop.py` | 201 | Tests for orchestration_loop — PersistentLoop stages wired to organism daemon. |
| `substrate/organism/tests/test_organism_events.py` | 59 | tests for organism ViewFrame event broadcasting. |
| `substrate/organism/tests/test_outcome_learning.py` | 211 | Tests for outcome learning loop. |
| `substrate/organism/tests/test_phase10_template_supply.py` | 829 | Phase 10.0 — Template Library, Candidate Supply, and Cockpit Route Extraction tests. |
| `substrate/organism/tests/test_phase11_1_universal_work.py` | 854 | Phase 11.1 — Universal Work Queue + Work Packet Engine tests. |
| `substrate/organism/tests/test_phase11_self_build_queue.py` | 661 | Phase 11.0 — Self-Build Engineering Queue tests. |
| `substrate/organism/tests/test_phase12_0_propagation_graph.py` | 989 | Phase 12.0 — Universal Propagation Graph / Correspondence Layer tests. |
| `substrate/organism/tests/test_phase13_0_operator_experience.py` | 841 | Phase 13.0 — Operator Experience Kernel tests. |
| `substrate/organism/tests/test_phase13_4m.py` | 614 | Phase 13.4M tests — multi-runtime operator acceptance correction. |
| `substrate/organism/tests/test_phase14_1_source_inspection.py` | 698 | Tests for Phase 14.1 — Permissioned Source Inspection Execution. |
| `substrate/organism/tests/test_phase3.py` | 749 | Phase 3 tests — Governed Recursive Execution Economy. |
| `substrate/organism/tests/test_phase58_integration.py` | 209 | Phase 5.8 integration tests — full Operational Leverage Engine. |
| `substrate/organism/tests/test_phase59_integration.py` | 116 | Integration tests for Phase 5.9 — end-to-end workload execution. |
| `substrate/organism/tests/test_phase61_governed_spine.py` | 686 | Tests for Phase 6.1 — GovernedExecutionSpine, ActionEnvelope, |
| `substrate/organism/tests/test_phase62_spine_enforcement.py` | 830 | Tests for Phase 6.2 — Execution Spine Enforcement + SpineGuard Ladder. |
| `substrate/organism/tests/test_phase63_autonomous_gate.py` | 594 | Phase 6.3 — Autonomous Execution Spine Gate tests. |
| `substrate/organism/tests/test_phase92_self_improvement.py` | 789 | Phase 9.2 — Governed Self-Improvement Trial tests. |
| `substrate/organism/tests/test_phase93_reliability_campaign.py` | 778 | Phase 9.3 — Self-Improvement Reliability Campaign tests. |
| `substrate/organism/tests/test_phase94_coherence_propagation.py` | 795 | Phase 9.4 tests — Template Registry, Agent Capability Model, Coherence Propagation. |
| `substrate/organism/tests/test_phase95_spine_native_propagation.py` | 1,473 | Phase 9.5 tests — Spine-Native Propagation + Template-Guided Improvement Campaign. |
| `substrate/organism/tests/test_phase9_integration.py` | 477 | Tests for Phase 9.0 — World Model → Execution Integration. |
| `substrate/organism/tests/test_plan_execution_adapter.py` | 769 | Tests for plan_execution_adapter — Phase 9.1 Composition→Execution bridge. |
| `substrate/organism/tests/test_projection_port.py` | 117 | Tests for projection-agnostic organism state port. |
| `substrate/organism/tests/test_projection_reconciliation_engine.py` | 449 | Tests for ProjectionReconciliationEngine (Phase 14.0). |
| `substrate/organism/tests/test_projection_source_registry.py` | 392 | Tests for ProjectionSourceRegistry (Phase 14.0). |
| `substrate/organism/tests/test_protocols.py` | 67 | tests for organism protocols — deliverable, agent message, worker spec. |
| `substrate/organism/tests/test_report_dispatcher.py` | 157 | Tests for substrate.organism.report_dispatcher. |
| `substrate/organism/tests/test_runtime_events.py` | 96 | Tests for runtime event bus wiring. |
| `substrate/organism/tests/test_runtime_graph.py` | 293 | Tests for RuntimeGraph — runtime registry, scoring, routing. |
| `substrate/organism/tests/test_runtime_supervisor.py` | 250 | Tests for RuntimeSupervisor — lifecycle management, crash detection, recovery. |
| `substrate/organism/tests/test_store.py` | 72 | tests for organism JSONL store. |
| `substrate/organism/tests/test_workcell_protocol.py` | 293 | Tests for WorkcellV2 — durable inbox/outbox execution cells. |
| `substrate/organism/tests/test_worker_cell.py` | 37 | tests for worker cell — bounded task execution. |
| `substrate/organism/tests/test_workload_probes.py` | 100 | Tests for WorkloadProbes. |
| `substrate/organism/tests/test_workload_runner.py` | 124 | Tests for the WorkloadRunner — Phase 5.9. |
| `substrate/organism/tests/test_world_model.py` | 275 | Tests for organism world model — system self-model. |
| `substrate/organism/tradeoff_intelligence_engine.py` | 563 | C14.1 — Tradeoff Intelligence Engine. |
| `substrate/organism/trajectory_intelligence_runtime.py` | 873 | Trajectory Intelligence Runtime — Campaign 13.0 |
| `substrate/organism/trial_runner.py` | 682 | Phase 9.3 — Self-Improvement Reliability Campaign Trial Runner. |
| `substrate/organism/trust_score.py` | 260 | Trust Score Engine — composite trust scoring via weakest-link gate. |
| `substrate/organism/umh_node_registry.py` | 149 | UMH Node Registry — canonical registry of UMH organism nodes. |
| `substrate/organism/umh_node_topology.py` | 235 | UMH Node Topology — canonical node role and version models. |
| `substrate/organism/umh_version_coherence.py` | 132 | UMH Version Coherence Engine — detects version drift across nodes. |
| `substrate/organism/universal_work_queue.py` | 342 | Universal Work Queue — canonical queue for all work packets. |
| `substrate/organism/work_graph.py` | 460 | Work Graph — read-only query projection over existing work stores. |
| `substrate/organism/work_packet.py` | 451 | Work Packet — canonical intent-to-execution container. |
| `substrate/organism/work_packet_engine.py` | 867 | Work Packet Engine — creates work packets from user intent. |
| `substrate/organism/work_portfolio_runtime.py` | 629 | Work Portfolio Runtime — execution health, velocity, and drift detection. |
| `substrate/organism/work_readiness_runtime.py` | 633 | Work Readiness Runtime — multi-dimensional readiness classification. |
| `substrate/organism/work_recovery_runtime.py` | 305 | Work Recovery Runtime — maps work states to recovery actions. |
| `substrate/organism/workcell.py` | 278 | Workcell — planning/delegation workcell model for Work Packets. |
| `substrate/organism/workcell_daemon.py` | 345 | WorkcellDaemon — persistent processor for workcell inboxes. |
| `substrate/organism/workcell_protocol.py` | 396 | WorkcellV2 — durable inbox/outbox execution cells. |
| `substrate/organism/worker_cell.py` | 46 | Worker cell — bounded task execution through the existing pipeline. |
| `substrate/organism/worker_lifecycle.py` | 112 | Worker Lifecycle Emitter — structured lifecycle events. |
| `substrate/organism/worker_registry.py` | 192 | Worker Registry — active worker inventory per device. |
| `substrate/organism/workload_placement_policy.py` | 393 | Workload placement policy — selects correct runtime + device for Work Packets. |
| `substrate/organism/workload_probes.py` | 327 | Real Workload Probes — live operational pressure into the organism. |
| `substrate/organism/workload_runner.py` | 850 | Real Workload Runner — governed execution of operational jobs. |
| `substrate/organism/workspace_awareness.py` | 251 | Workspace Awareness Runtime — deterministic active-context detection. |
| `substrate/organism/workstation_runtime.py` | 1,400 | Workstation Runtime — canonical workstation planning layer (Phase 10). |
| `substrate/organism/worktree_sandbox.py` | 455 | Worktree Sandbox Manager — isolated execution environments for autonomous improvements. |
| `substrate/organism/world_model.py` | 647 | World Model — organism-level self-model of UMH system state. |

## substrate/reality_model/ (8 files)

| Path | Lines | Purpose |
|---|---|---|
| `substrate/reality_model/__init__.py` | 36 | Reality Model — dual Canonical/Instance reality modeling. |
| `substrate/reality_model/canonical.py` | 220 | Canonical Reality Model — compressed, reusable intelligence. |
| `substrate/reality_model/canonical_reality_write.py` | 179 | Canonical reality write path — governed entry point for non-execution observations. |
| `substrate/reality_model/instance.py` | 187 | Instance Reality Model — live operational truth of one user/company/environment. |
| `substrate/reality_model/reality_intelligence.py` | 678 | Reality Intelligence Engine — read-only retrieval and explanation. |
| `substrate/reality_model/reality_mutation.py` | 63 | Reality mutation contracts — governed observation writes. |
| `substrate/reality_model/reality_query.py` | 58 | Reality Query Contract — types for reality interrogation. |
| `substrate/reality_model/simulation.py` | 325 | Simulation Reality — non-mutating hypothesis testing. |

## substrate/sockets/ (26 files)

| Path | Lines | Purpose |
|---|---|---|
| `substrate/sockets/__init__.py` | 43 | UMH Socket Layer — typed boundary between substrate and integrations. |
| `substrate/sockets/approval_port.py` | 100 | Approval port — substrate-layer trust boundary for approval decisions. |
| `substrate/sockets/browser_port.py` | 25 | Browser port — substrate-layer abstraction for web access adapters. |
| `substrate/sockets/capability_socket.py` | 109 | Capability socket — bidirectional execution for integration capabilities. |
| `substrate/sockets/channel_port.py` | 23 | Channel port — substrate-layer abstraction for the channel router. |
| `substrate/sockets/config_port.py` | 69 | Config port — substrate-layer abstraction for runtime config access. |
| `substrate/sockets/data_source_port.py` | 132 | Data source port — substrate-layer abstraction for external data adapters. |
| `substrate/sockets/envelopes.py` | 103 | Envelope dataclasses — the data shapes that cross the socket boundary. |
| `substrate/sockets/intelligence_port.py` | 177 | Intelligence port — substrate-layer abstraction for model routing and LLM access. |
| `substrate/sockets/mesh_dispatch_port.py` | 146 | Mesh dispatch port — substrate-layer abstraction for governed remote dispatch. |
| `substrate/sockets/message_port.py` | 29 | Message port — substrate-layer abstraction for conversation persistence. |
| `substrate/sockets/notification.py` | 91 | Notification socket — substrate-layer abstraction for outbound notifications. |
| `substrate/sockets/notification_engine.py` | 245 | Multi-channel notification engine — substrate-layer abstraction. |
| `substrate/sockets/organism_port.py` | 24 | Organism port — substrate-layer abstraction for daemon/organism access. |
| `substrate/sockets/outcome_socket.py` | 80 | Outcome socket — outbound result notifications to integrations. |
| `substrate/sockets/projection_port.py` | 472 | Projection Port — abstract consumption layer for projections. |
| `substrate/sockets/protocols.py` | 128 | Protocol definitions for integration-side contracts. |
| `substrate/sockets/registry.py` | 179 | Integration registry — central registration and generic adapter bridge. |
| `substrate/sockets/remote_exec_port.py` | 50 | Remote execution port — substrate-layer abstraction for SSH and remote ops. |
| `substrate/sockets/sensing_port.py` | 67 | Sensing adapter port — substrate-layer abstraction for perception registration. |
| `substrate/sockets/signal_socket.py` | 108 | Signal socket — inbound intake for external integrations. |
| `substrate/sockets/tool_adapter_port.py` | 27 | Tool adapter port — substrate-layer abstraction for shell/filesystem/git tools. |
| `substrate/sockets/view/__init__.py` | 1 | View socket broadcast infrastructure — sync→async bridge and WebSocket endpoint. |
| `substrate/sockets/view/broadcaster.py` | 146 | Broadcaster — sync→async bridge for ViewFrame delivery. |
| `substrate/sockets/view/websocket.py` | 95 | WebSocket endpoint for broadcasting ViewFrames to cockpit clients. |
| `substrate/sockets/view_socket.py` | 62 | View socket — broadcast pipeline state frames to observers. |

## substrate/state/ (66 files)

| Path | Lines | Purpose |
|---|---|---|
| `substrate/state/README.md` | 37 | state/ |
| `substrate/state/__init__.py` | 0 | package marker (empty) |
| `substrate/state/business/__init__.py` | 0 | package marker (empty) |
| `substrate/state/business/business_instance.py` | 489 | BusinessInstance — venture-stage context layer. |
| `substrate/state/business/primitives.py` | 923 | Primitives — stage-aware business rules and contextual reasoning engine. |
| `substrate/state/business/venture_knowledge.py` | 200 | VentureKnowledgeBase — loads venture profiles from instance JSON; resolves venture names and metadata |
| `substrate/state/config/__init__.py` | 27 | UMH Config Store — layered configuration with runtime mutability. |
| `substrate/state/config/config_store.py` | 183 | ConfigStore — layered JSON-file-backed configuration. |
| `substrate/state/config/settings_persistence.py` | 133 | Settings Persistence — flock + atomic write for settings domains. |
| `substrate/state/context/__init__.py` | 0 | package marker (empty) |
| `substrate/state/context/context.py` | 59 | SubstrateContext — org/venture runtime context loaded from UMH_ORG_ID/UMH_USER_ID env |
| `substrate/state/finance/__init__.py` | 0 | package marker (empty) |
| `substrate/state/finance/expense_tracker.py` | 444 | Expense Tracker — processes receipts from Gmail RECEIPTS-FINANCIALS folder, |
| `substrate/state/finance/subscription_tracker.py` | 121 | Subscription Tracker — maintains a registry of active |
| `substrate/state/lifecycle/__init__.py` | 0 | package marker (empty) |
| `substrate/state/lifecycle/stage_manager.py` | 286 | StageManager — auto-updates Notion, Discord, and primitives when stage advances. |
| `substrate/state/logs/__init__.py` | 0 | package marker (empty) |
| `substrate/state/logs/decision_log.py` | 210 | DecisionLog — permanent record of important decisions made in conversation. |
| `substrate/state/memory/__init__.py` | 0 | package marker (empty) |
| `substrate/state/memory/contracts/__init__.py` | 0 | package marker (empty) |
| `substrate/state/memory/contracts/canonical_memory_query_contracts.py` | 207 | Canonical Memory Query contracts for the UMH substrate layer. |
| `substrate/state/memory/contracts/canonical_memory_reconciliation_engine_v1.py` | 529 | Canonical Memory Reconciliation Engine v1. |
| `substrate/state/memory/contracts/canonical_memory_store_v1.py` | 289 | Canonical Memory Store v1 — append-only, replay-safe, queryable memory persistence. |
| `substrate/state/memory/contracts/memory_conflict_governance_v1.py` | 167 | Memory Conflict Governance v1. |
| `substrate/state/memory/contracts/memory_identity_v1.py` | 100 | Memory Identity v1 — deterministic identity model for canonical memories. |
| `substrate/state/memory/memory.py` | 1,039 | Persistent memory for OS agents — backed by Neon (PostgreSQL). |
| `substrate/state/metrics/__init__.py` | 0 | package marker (empty) |
| `substrate/state/metrics/founder_rate.py` | 284 | Founder Rate — framework for valuing |
| `substrate/state/metrics/okr_tracker.py` | 114 | OKR Tracker — tracks Objectives and Key Results per venture. |
| `substrate/state/permissions/__init__.py` | 0 | package marker (empty) |
| `substrate/state/permissions/os_trinity.py` | 381 | OSTrinity — OS Trinity harness layer. |
| `substrate/state/preferences/__init__.py` | 0 | package marker (empty) |
| `substrate/state/preferences/model_preferences.py` | 447 | Multi-model router with business context awareness and full human override. |
| `substrate/state/profiles/__init__.py` | 0 | package marker (empty) |
| `substrate/state/profiles/user_model.py` | 454 | UserModel — learns how the founder thinks, communicates, and makes decisions. |
| `substrate/state/providers/__init__.py` | 0 | package marker (empty) |
| `substrate/state/providers/provider_state.py` | 287 | Global Provider State + Backpressure + Execution Budget. |
| `substrate/state/registries/__init__.py` | 0 | package marker (empty) |
| `substrate/state/registries/claude_skill_registry.py` | 241 | ClaudeSkillRegistry — tracks all .claude/skills files, syncs them to Neon, |
| `substrate/state/registries/skill_registry.py` | 254 | SkillRegistry — per-org skill catalog with load/reset accessors |
| `substrate/state/registries/skill_registry_v2.py` | 478 | SkillRegistryV2 — first-class skill objects with trust scoring, |
| `substrate/state/session/__init__.py` | 0 | package marker (empty) |
| `substrate/state/session/session_state.py` | 89 | SessionState — persistent session key/value state backed by session_state.json |
| `substrate/state/storage/__init__.py` | 0 | package marker (empty) |
| `substrate/state/storage/db.py` | 129 | Neon (PostgreSQL) connection layer for the Python AI layer. |
| `substrate/state/stores/agent_registry_store.py` | 27 | AgentRegistryStore — canonical write API for the agents table. |
| `substrate/state/stores/approval_store.py` | 83 | ApprovalStore — SQL-backed multi-tenant approval API (deprecated). |
| `substrate/state/stores/context_compaction_store.py` | 37 | ContextCompactionStore — canonical write API for the context_compactions table. |
| `substrate/state/stores/email_folder_store.py` | 46 | EmailFolderStore — canonical write API for the email_folders table. |
| `substrate/state/stores/embedding_store.py` | 36 | EmbeddingStore — canonical write API for the embeddings table. |
| `substrate/state/stores/entity_link_store.py` | 39 | EntityLinkStore — canonical write API for the entity_links table. |
| `substrate/state/stores/entity_store.py` | 335 | EntityStore — persistence layer for the entity hierarchy. |
| `substrate/state/stores/goal_store.py` | 188 | GoalStore — canonical write API for the goals and goal_outcomes tables. |
| `substrate/state/stores/higgsfield_store.py` | 49 | HiggsFieldStore — canonical write API for the higgsfield_jobs table. |
| `substrate/state/stores/permission_store.py` | 114 | PermissionStore — canonical write API for cross_product_permissions and product_connections tables. |
| `substrate/state/stores/preference_store.py` | 46 | PreferenceStore — canonical write API for the model_preferences table. |
| `substrate/state/stores/profile_store.py` | 148 | ProfileStore — canonical write API for human_profiles, user_profiles, user_intelligence_profiles. |
| `substrate/state/stores/skill_store.py` | 80 | SkillStore — canonical API for the skills table. |
| `substrate/state/stores/task_store.py` | 83 | TaskStore — canonical write API for the tasks table. |
| `substrate/state/stores/venture_store.py` | 36 | VentureStore — canonical write API for the ventures table. |
| `substrate/state/stores/watermark_store.py` | 75 | Generic watermark persistence — thread-safe JSONL append-log for per-key poll |
| `substrate/state/tenancy/__init__.py` | 0 | package marker (empty) |
| `substrate/state/tenancy/tenant.py` | 145 | Tenant — formal multi-tenant isolation layer for EOS. |
| `substrate/state/transformation_state_ledger.py` | 383 | Transformation State Ledger for the UMH substrate layer. |
| `substrate/state/work/__init__.py` | 0 | package marker (empty) |
| `substrate/state/work/work_state.py` | 225 | Work State Detection + Idle Gate + Adaptive Throttling. |

## substrate/templates/ (3 files)

| Path | Lines | Purpose |
|---|---|---|
| `substrate/templates/__init__.py` | 44 | substrate.templates — the RealityTemplate metamodel home (packet P4S-12). |
| `substrate/templates/reality_template.py` | 449 | RealityTemplate metamodel types — the L2 ontology of provable patterns. |
| `substrate/templates/registry.py` | 218 | RealityTemplate registry — load, validate, resolve, and evolve templates. |

## substrate/understanding/ (55 files)

| Path | Lines | Purpose |
|---|---|---|
| `substrate/understanding/README.md` | 33 | understanding/ |
| `substrate/understanding/__init__.py` | 0 | package marker (empty) |
| `substrate/understanding/breadth_expansion.py` | 186 | Breadth Expansion Engine — step 9 of the 27-step spine. |
| `substrate/understanding/deliberation/__init__.py` | 0 | package marker (empty) |
| `substrate/understanding/deliberation/council.py` | 528 | Deliberation Council — 7-role multi-perspective advisory system. |
| `substrate/understanding/domains/__init__.py` | 14 | Domain bridge — maps ontology observations to domain-typed projections. |
| `substrate/understanding/domains/business.py` | 245 | Business domain bridge — structural mapping from ontology to business primitives. |
| `substrate/understanding/domains/contract.py` | 74 | Domain bridge protocol and projection dataclass. |
| `substrate/understanding/domains/creator.py` | 515 | Creator domain bridge — structural mapping from ontology to creator primitives. |
| `substrate/understanding/domains/life.py` | 568 | Life domain bridge — structural mapping from ontology to life primitives. |
| `substrate/understanding/domains/registry.py` | 31 | Bridge registry — plug-in system for domain bridges. |
| `substrate/understanding/embedding/__init__.py` | 0 | package marker (empty) |
| `substrate/understanding/embedding/embedder.py` | 69 | Lightweight text embedder — shared singleton used by memory.py and |
| `substrate/understanding/embedding/embedding_engine.py` | 400 | EmbeddingEngine — Three-tier hybrid embedding with graceful degradation. |
| `substrate/understanding/intelligence/__init__.py` | 0 | package marker (empty) |
| `substrate/understanding/intelligence/competitive_intel.py` | 144 | Competitive Intelligence — tracks competitor signals |
| `substrate/understanding/intelligence/human_intelligence.py` | 709 | HumanIntelligenceEngine — behavioral profiling for every person the system |
| `substrate/understanding/intelligence/input_intelligence.py` | 348 | Input Intelligence Layer |
| `substrate/understanding/intelligence/person_recognition.py` | 599 | Person Recognition — central module for identifying known people |
| `substrate/understanding/intelligence/stakeholder_map.py` | 248 | Stakeholder Map — tracks key stakeholders per venture, |
| `substrate/understanding/interpretation/__init__.py` | 0 | package marker (empty) |
| `substrate/understanding/interpretation/interpretation_engine_v1.py` | 551 | Interpretation Engine v1 for the UMH substrate layer. |
| `substrate/understanding/knowledge/__init__.py` | 0 | package marker (empty) |
| `substrate/understanding/knowledge/knowledge_domains.py` | 1,126 | KnowledgeDomainRegistry — base equilibrium awareness layer. |
| `substrate/understanding/knowledge/knowledge_graph.py` | 521 | KnowledgeGraph — entity relationship layer for EOS. |
| `substrate/understanding/knowledge/knowledge_integrator.py` | 237 | KnowledgeIntegrator — permanent knowledge accumulation layer. |
| `substrate/understanding/knowledge/knowledge_layers.py` | 477 | Knowledge Layer Engine — behavioral distillation layers 6-17. |
| `substrate/understanding/knowledge/philosophy_lenses.py` | 382 | Philosophy Lens Engine — codified lenses from PHILOSOPHY.md Section VII. |
| `substrate/understanding/ontology/__init__.py` | 0 | package marker (empty) |
| `substrate/understanding/patterns/__init__.py` | 0 | package marker (empty) |
| `substrate/understanding/patterns/leverage_patterns.py` | 119 | Leverage Pattern Detection — identifies Leverage Killer |
| `substrate/understanding/patterns/pattern_engine.py` | 205 | PatternEngine — cross-session behavioral pattern detection. |
| `substrate/understanding/perception/__init__.py` | 0 | package marker (empty) |
| `substrate/understanding/perception/multimodal.py` | 253 | Multi-modal understanding — turn operator-attached media into meaning. |
| `substrate/understanding/perception/orchestrator.py` | 1,157 | GenericIngestionOrchestrator — source-agnostic canonical pipeline. |
| `substrate/understanding/perception/parsers/__init__.py` | 38 | Modular parser system for the EOS codebase knowledge graph. |
| `substrate/understanding/perception/parsers/base.py` | 57 | Shared contracts for all language parsers. |
| `substrate/understanding/perception/parsers/config_parser.py` | 51 | Config parser — top-level key extraction for JSON/YAML/TOML files. |
| `substrate/understanding/perception/parsers/js_parser.py` | 95 | JavaScript parser — regex-based symbol + import extraction. |
| `substrate/understanding/perception/parsers/python_parser.py` | 125 | Python parser — wraps the existing AST scanner in codebase_graph.py. |
| `substrate/understanding/perception/parsers/sql_parser.py` | 53 | SQL parser — detects tables, views, and FROM references. |
| `substrate/understanding/perception/parsers/ts_parser.py` | 33 | TypeScript parser — reuses JS regexes and adds interface/type extraction. |
| `substrate/understanding/perception/primitive_decomposition_v1.py` | 104 | Primitive Decomposition v1 for the UMH substrate layer. |
| `substrate/understanding/perception/source.py` | 33 | Source abstraction for the generic ingestion pipeline. |
| `substrate/understanding/reality/__init__.py` | 0 | package marker (empty) |
| `substrate/understanding/reality/reality_context.py` | 153 | RealityContext — ambient present-state snapshot. |
| `substrate/understanding/reality/reality_engine.py` | 589 | RealityIntelligenceEngine — continuous market intelligence layer. |
| `substrate/understanding/research/__init__.py` | 0 | package marker (empty) |
| `substrate/understanding/research/research_engine.py` | 678 | ResearchEngine — autonomous knowledge gap detection and research layer. |
| `substrate/understanding/signals/__init__.py` | 0 | package marker (empty) |
| `substrate/understanding/signals/founder_capture.py` | 227 | Founder Capture — detects tasks, ideas, and reminders from Discord messages |
| `substrate/understanding/world_model/__init__.py` | 0 | package marker (empty) |
| `substrate/understanding/world_model/world_model.py` | 268 | Domain-knowledge world model — two-layer world model for the Meta Harness. |
| `substrate/understanding/world_pulse/__init__.py` | 0 | package marker (empty) |
| `substrate/understanding/world_pulse/world_pulse.py` | 605 | WorldPulse — continuous market and creator intelligence monitoring. |

## substrate/workstation/ (57 files)

| Path | Lines | Purpose |
|---|---|---|
| `substrate/workstation/__init__.py` | 17 | Workstation state — profile, session, and resume snapshots. |
| `substrate/workstation/activation.py` | 214 | Activation signal and presence session for workstation control. |
| `substrate/workstation/agent_workforce_runtime.py` | 344 | Agent Workforce Runtime — Campaign 19.1. |
| `substrate/workstation/ambient_wake_runtime.py` | 407 | Ambient Wake Runtime — Campaign 20.2. |
| `substrate/workstation/app_resolver.py` | 229 | Native app resolver — Chrome-first browser policy, app vs website classification. |
| `substrate/workstation/attention_aggregation_runtime.py` | 255 | Attention Aggregation Runtime — Campaign 18.2. |
| `substrate/workstation/attention_vision_runtime.py` | 364 | Attention Vision Runtime — Campaign 21.3. |
| `substrate/workstation/camera_commands.py` | 647 | Camera command dispatcher — routes CAMERA_CONTROL intents to operations. |
| `substrate/workstation/checkpoint.py` | 151 | Continuity checkpoint — state snapshot on continuity transitions. |
| `substrate/workstation/cockpit_capability_map.py` | 420 | Cockpit Capability Map — audit surface for cockpit routes, panels, stores. |
| `substrate/workstation/command_center_mvp_runtime.py` | 389 | Command Center MVP Runtime — operator landing surface. |
| `substrate/workstation/command_router.py` | 1,167 | Command router — natural language command classification and routing. |
| `substrate/workstation/continuity.py` | 214 | Continuity state machine — unified lifecycle for operator presence/absence. |
| `substrate/workstation/continuity_engine.py` | 583 | Continuity engine — orchestrator binding all continuity subsystems. |
| `substrate/workstation/device_presence.py` | 162 | Device presence registry for active cockpit sessions. |
| `substrate/workstation/environment_awareness_runtime.py` | 362 | Environment Awareness Runtime — Campaign 21.1. |
| `substrate/workstation/execution_fabric_runtime.py` | 338 | Execution Fabric Runtime — Campaign 19.0. |
| `substrate/workstation/file_browser.py` | 220 | Safe read-only file browser with allowlisted root paths. |
| `substrate/workstation/intent_contract.py` | 258 | Intent contract — converts high-level operator intent into end-state designs. |
| `substrate/workstation/jarvis_command.py` | 5 | Backward-compat shim — canonical module is command_router.py. |
| `substrate/workstation/lifecycle_modes.py` | 50 | Lifecycle modes — system-level cycle that governs safety and background behavior. |
| `substrate/workstation/loop_engine.py` | 283 | Loop completion engine — end-state verification and progress reporting. |
| `substrate/workstation/meta_ide_context_runtime.py` | 272 | Meta IDE Context Runtime — read-only context binding for the build surface. |
| `substrate/workstation/meta_ide_projection_loop_runtime.py` | 342 | Meta IDE Projection Build Loop Runtime — governed build from inside cockpit. |
| `substrate/workstation/mode_commands.py` | 114 | Mode switching via natural typed commands. |
| `substrate/workstation/mode_resolver.py` | 203 | Workstation mode resolver — authoritative composite of all mode systems. |
| `substrate/workstation/mvp_readiness_runtime.py` | 443 | MVP Readiness Runtime — objective MVP readiness scoring across 14 dimensions. |
| `substrate/workstation/operating_loop_runtime.py` | 300 | Operating Loop Runtime — visibility layer over existing execution systems. |
| `substrate/workstation/orchestrator_presence_runtime.py` | 395 | Orchestrator Presence Runtime — persistent presence layer for the primary orchestrator. |
| `substrate/workstation/overnight_queue.py` | 196 | Overnight safe-work queue scaffold — thin MVP for queuing permitted work. |
| `substrate/workstation/profile_behavior.py` | 224 | Profile behavior configs — per-profile policies for voice, camera, notifications, apps. |
| `substrate/workstation/profile_modes.py` | 35 | Profile/work modes — operator activity context governing workspace/tool/task selection. |
| `substrate/workstation/resume_brief.py` | 288 | Return/resume brief generator — answers "what happened while I was gone?" |
| `substrate/workstation/screen_awareness_runtime.py` | 282 | Screen Awareness Runtime — Campaign 21.0. |
| `substrate/workstation/security_mode.py` | 218 | Security Harden mode — governed security posture for the cockpit. |
| `substrate/workstation/session_machine_runtime.py` | 330 | Session Machine Runtime — Campaign 19.2. |
| `substrate/workstation/state.py` | 221 | Workstation state — profile, session, and resume state. |
| `substrate/workstation/tracker_stack.py` | 243 | Tracker stack — independent, stackable vision trackers. |
| `substrate/workstation/trigger_chains.py` | 394 | Trigger chain engine — deterministic event→condition→action chains. |
| `substrate/workstation/unified_approval_runtime.py` | 492 | Unified Approval Runtime — single approval queue across all UMH subsystems. |
| `substrate/workstation/unified_execution_surface_runtime.py` | 489 | Unified Execution Surface Runtime — single view across all execution subsystems. |
| `substrate/workstation/unified_workstation_runtime.py` | 336 | Unified Workstation Runtime — Campaign 18.0. |
| `substrate/workstation/vision_presets.py` | 327 | Vision Preset Studio — full CRUD for camera presets. |
| `substrate/workstation/vision_privacy.py` | 237 | Vision privacy governance — hard-coded rules for camera usage. |
| `substrate/workstation/vision_query.py` | 269 | Vision query handler — grounded visual question answering. |
| `substrate/workstation/vision_scene.py` | 529 | Vision scene model — grounded workspace state from camera frames. |
| `substrate/workstation/visual_context_runtime.py` | 392 | Visual Context Runtime — Campaign 21.2. |
| `substrate/workstation/visual_operations_runtime.py` | 364 | Visual Operations Runtime — Campaign 21.4 (composition root). |
| `substrate/workstation/voice_consent.py` | 194 | Voice consent grants — P4S-31D-1 (VoiceIntentContract consent gate). |
| `substrate/workstation/voice_ingress_runtime.py` | 352 | Voice Ingress Runtime — Campaign 20.0. |
| `substrate/workstation/voice_operations_runtime.py` | 462 | Voice Operations Runtime — Campaign 20.4 (composition root). |
| `substrate/workstation/voice_output_runtime.py` | 265 | Voice Output Runtime — Campaign 20.3. |
| `substrate/workstation/voice_route_resolver.py` | 279 | Voice route resolver — separates execution target from audio output device. |
| `substrate/workstation/voice_session_manager.py` | 367 | Voice Session Manager — Campaign 20.1. |
| `substrate/workstation/vps_control_catalog.py` | 649 | VPS control catalog — governed command execution on the VPS node. |
| `substrate/workstation/work_lane.py` | 514 | Work lane model — multi-session lane routing and foreground guard. |
| `substrate/workstation/workstation_presence_runtime.py` | 289 | Workstation Presence Runtime — operator footprint across the workstation. |
