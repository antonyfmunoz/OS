# Census: substrate/execution/ and substrate/control_plane/

**Scope:** 121 execution modules + 58 control_plane modules (excluding `__init__.py`, `_dormant/`, tests, `__pycache__`).

**Reachability note:** The pre-computed reachability set (73 execution + 28 control_plane PRODUCTION_ACTIVE) was derived from a narrow entry-point graph (running Docker services only). Direct importer analysis against `services/`, `transports/`, `scripts/`, and `adapters/` shows a much larger reachable surface — the substrate public API (`substrate/__init__.py`), the transports API layer (`transports/api/*`, `transports/presence/*`, `transports/discord/*`), and operator/cockpit route handlers pull in nearly the entire directory tree. Status below reflects **actual importer reachability**, which supersedes the narrow set. Where a module is imported only by proof/certification or dry-run scripts, it is marked PARTIALLY_INTEGRATED.

---

## substrate/execution/ (121 modules)

### execution/actuation/ (4 modules)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| actuator_backend_registry_v1 | execution | PARTIALLY_INTEGRATED | Selects best GUI actuation backend for a request (chrome launch, window focus, screenshot) without executing. | substrate/execution/actuation |
| actuator_maturity_v1 | governance | PARTIALLY_INTEGRATED | L0–L7 maturity model that caps an actuator's claimed maturity to the evidence it produced. | substrate/execution/actuation |
| observed_desktop_state_v1 | perception | PARTIALLY_INTEGRATED | Captures REAL observed Windows desktop state + maturity classification + proof-evidence extraction. | substrate/execution/actuation |
| windows_foreground_actuator_v1 | execution | PARTIALLY_INTEGRATED | Orchestrates live Windows GUI actuation via PowerShell relay, classifies result against maturity ceiling. | substrate/execution/actuation |

*Reachable via `transports/presence/handlers/reports/adapter.py` and workstation orchestrator chain. Evidence-only path (no running service tick), hence PARTIALLY_INTEGRATED.*

### execution/adapters/ (1 module)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| physical | infrastructure | DORMANT | Contract + registry for physical/IoT adapters (home automation, vehicle, health, smart devices). No importers. | adapters/ (extension point) |

*No importers anywhere. Extension-point scaffolding for a future hardware layer. Unique framework, zero wiring → PROMOTE candidate or ARCHIVE.*

### execution/agents/ (2 modules)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| browser_agent | execution | PRODUCTION_ACTIVE | Playwright web operator wrapper giving agents navigate/extract/act on any website. | substrate/execution/agents |
| computer_use_agent | execution | DORMANT | Screenshot→vision-LLM→governance-gated action loop; Container + Native implementations. | substrate/execution/agents |

*computer_use_agent has no runtime importer (only the dependency-direction check script references it). Unique governed vision-action loop → PROMOTE (this is the intended computer-use spine) or MERGE with browser_agent.*

### execution/bridge/ (68 modules)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| actions | execution | PRODUCTION_ACTIVE | Bridge action primitives (SPEAK/PLAY/OPEN/LAUNCH) for station/scene layer. | execution/bridge |
| app_allowlist | governance | PRODUCTION_ACTIVE | Allow-list of launchable apps for station actions. | execution/bridge |
| audio_loop | execution | PRODUCTION_ACTIVE | Audio capture/playback loop for voice-first station. | execution/bridge |
| auto_task_generation | planning | PRODUCTION_ACTIVE | Generates tasks automatically from operator context. | execution/bridge |
| browser_agent | execution | PRODUCTION_ACTIVE | Bridge-layer wrapper wiring browser_agent into station capabilities. | execution/bridge |
| capabilities | execution | PRODUCTION_ACTIVE | Station capability registry. | execution/bridge |
| capability_routing | reasoning | PRODUCTION_ACTIVE | Routes a request to the right station capability. | execution/bridge |
| capability_tagging | understanding | PRODUCTION_ACTIVE | Tags requests with capability metadata. | execution/bridge |
| claude_responder | execution | PRODUCTION_ACTIVE | Generates Claude responses for the bridge/session layer. | execution/bridge |
| claude_session_bridge | execution | PRODUCTION_ACTIVE | Bridges a live Claude CLI session into the station. | execution/bridge |
| context_lifecycle | memory | PRODUCTION_ACTIVE | Manages per-session context lifecycle. | execution/bridge |
| day_workflows | planning | PRODUCTION_ACTIVE | Open/close-day workflow definitions. | execution/bridge |
| discord_mode_routing | reasoning | PRODUCTION_ACTIVE | Routes Discord messages by operator mode. | execution/bridge |
| discord_output_policy | governance | DORMANT | Display-name normalization for Discord watcher output (strips cc_/session_ prefixes). | execution/bridge |
| discord_text_transport | infrastructure | PRODUCTION_ACTIVE | Text transport for Discord bridge. | execution/bridge |
| discord_voice_playback | execution | PRODUCTION_ACTIVE | Voice playback into Discord voice channels. | execution/bridge |
| discord_voice_transport | infrastructure | PRODUCTION_ACTIVE | Voice transport for Discord bridge. | execution/bridge |
| event_spine | infrastructure | PRODUCTION_ACTIVE | Event backbone for bridge subsystem. | execution/bridge |
| execution_trace | reflection | PRODUCTION_ACTIVE | Records bridge execution traces. | execution/bridge |
| live_sessions | infrastructure | PRODUCTION_ACTIVE | Tracks live interactive sessions. | execution/bridge |
| local_control | execution | PRODUCTION_ACTIVE | Local node control commands. | execution/bridge |
| local_listener | perception | PARTIALLY_INTEGRATED | Bounded wake/activation layer (hotkey/manual/simulated wake) starting rituals via readiness+scene policy. | execution/bridge |
| memory_scope_contracts | governance | PRODUCTION_ACTIVE | Memory-promotion scope enum (instance vs canon) gating what may become global UMH canon. | substrate/organism (memory promotion) |
| mode_behavior | reasoning | PRODUCTION_ACTIVE | Behavior policy per operator mode. | execution/bridge |
| node_controller | execution | PRODUCTION_ACTIVE | Controls mesh nodes from bridge. | execution/bridge |
| node_transport | infrastructure | PRODUCTION_ACTIVE | Node-to-node transport for bridge. | execution/bridge |
| nodes | infrastructure | PRODUCTION_ACTIVE | Node registry/state for bridge. | execution/bridge |
| operator_presence | execution | PRODUCTION_ACTIVE | Deterministic intro/outro presence lines on operator state transitions (no LLM). | execution/bridge |
| operator_session | infrastructure | PRODUCTION_ACTIVE | Operator session lifecycle. | execution/bridge |
| operator_state | world-model | PRODUCTION_ACTIVE | Operator state machine (the "experience is the state machine"). | execution/bridge |
| operator_transitions | reasoning | PRODUCTION_ACTIVE | Computes valid operator-state transitions. | execution/bridge |
| perception | perception | PRODUCTION_ACTIVE | Perception intake for the bridge. | execution/bridge |
| pipeline_execution | execution | PRODUCTION_ACTIVE | Executes bridge task pipelines. | execution/bridge |
| playback_status | perception | PRODUCTION_ACTIVE | Tracks audio playback status. | execution/bridge |
| resource_guard | governance | PRODUCTION_ACTIVE | Guards resource usage in station. | execution/bridge |
| result_query | memory | PRODUCTION_ACTIVE | Queries stored execution results. | execution/bridge |
| result_store | memory | PRODUCTION_ACTIVE | Persists execution results. | execution/bridge |
| ritual_body | execution | PARTIALLY_INTEGRATED | Maps ritual lifecycle events → bounded safe station actions (declarative RitualPolicy). | execution/bridge |
| ritual_inference | reasoning | PRODUCTION_ACTIVE | Infers which ritual applies from context. | execution/bridge |
| ritual_runner | execution | PARTIALLY_INTEGRATED | Shell-callable open_day/close_day ritual entry points for cron. | execution/bridge |
| rituals | planning | PRODUCTION_ACTIVE | Ritual registry + lifecycle (open_day/close_day). | execution/bridge |
| roles | governance | PRODUCTION_ACTIVE | Role definitions for station agents. | execution/bridge |
| scene_capabilities | execution | PRODUCTION_ACTIVE | Capabilities available per scene. | execution/bridge |
| scene_policy | governance | PRODUCTION_ACTIVE | Deterministic scene-selection policy from readiness. | execution/bridge |
| scenes | world-model | PRODUCTION_ACTIVE | Scene definitions and state. | execution/bridge |
| session_control | execution | PRODUCTION_ACTIVE | Start/stop/manage sessions. | execution/bridge |
| session_discord_bridge | infrastructure | PRODUCTION_ACTIVE | Bridges sessions to Discord. | execution/bridge |
| session_watcher | perception | PRODUCTION_ACTIVE | Watches CC/session state for the bridge. | execution/bridge |
| station | world-model | PRODUCTION_ACTIVE | Core station abstraction (the operator's physical presence). | execution/bridge |
| station_bus | infrastructure | PRODUCTION_ACTIVE | Message bus for station. | execution/bridge |
| station_daemon | infrastructure | PRODUCTION_ACTIVE | Long-running station daemon. | execution/bridge |
| station_helpers | infrastructure | PRODUCTION_ACTIVE | Shared station utilities. | execution/bridge |
| station_presence | perception | PRODUCTION_ACTIVE | Tracks station presence state. | execution/bridge |
| station_readiness | world-model | PRODUCTION_ACTIVE | Computes station readiness for scene policy. | execution/bridge |
| storage | memory | PRODUCTION_ACTIVE | Bridge-local persistence layer. | execution/bridge |
| target_policy | governance | PRODUCTION_ACTIVE | Policy for valid action targets. | execution/bridge |
| task_decomposition | planning | PARTIALLY_INTEGRATED | Deterministic keyword→template task decomposition (builder/product/ceo pipelines, zero LLM). | execution/bridge |
| task_execution | execution | PRODUCTION_ACTIVE | Executes decomposed tasks. | execution/bridge |
| task_pipeline | execution | PRODUCTION_ACTIVE | Pipeline model for task steps. | execution/bridge |
| task_queue | execution | PRODUCTION_ACTIVE | Queue for bridge tasks. | execution/bridge |
| task_system | execution | PRODUCTION_ACTIVE | Overall bridge task system. | execution/bridge |
| transcript_inject | memory | PRODUCTION_ACTIVE | Injects transcripts into session context. | execution/bridge |
| tts_sanitize | execution | PRODUCTION_ACTIVE | Sanitizes text before TTS. | execution/bridge |
| voice_eos_responder | execution | PRODUCTION_ACTIVE | Generates voice responses. | execution/bridge |
| voice_first | execution | PRODUCTION_ACTIVE | Voice-first interaction orchestration. | execution/bridge |
| voice_session | execution | PRODUCTION_ACTIVE | Voice session lifecycle in bridge. | execution/bridge |
| wake_producer | perception | PRODUCTION_ACTIVE | Produces wake events (feeds local_listener). | execution/bridge |
| workflow_delegation | planning | PRODUCTION_ACTIVE | Delegates workflow steps to agents/nodes. | execution/bridge |
| workflow_execution | execution | PRODUCTION_ACTIVE | Executes multi-step workflows. | execution/bridge |
| workload_policy | governance | PRODUCTION_ACTIVE | Policy governing station workload. | execution/bridge |

### execution/loop/ (3 modules)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| execution_loop | execution | PARTIALLY_INTEGRATED | Closed-loop goal→plan→execute→outcome→reselect cycle; "only Executor acts" rule. | execution/loop |
| persistent_loop | execution | PRODUCTION_ACTIVE | Config-driven runtime loops as capabilities (LoopDefinition + STAGE_REGISTRY). | execution/loop |
| stages | execution | PRODUCTION_ACTIVE | Built-in composable loop stages (signal_drain, goal_execution, research_cycle). | execution/loop |

*persistent_loop + stages reachable via operator_api, cockpit_execution_loop_routes, autonomous_tick. execution_loop only referenced by canonical_types → PARTIALLY_INTEGRATED (superseded by persistent_loop).*

### execution/media/ (1 module)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| media_processor | perception | PRODUCTION_ACTIVE | Unified multimodal file router (whisper for audio, Gemini for image/video/doc, embeddings). | execution/media |

### execution/runtime/ (17 modules)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| capability_router | reasoning | PRODUCTION_ACTIVE | Intent→best-tool routing with ranked provider chains, falls through to LLM router. Canonical `Capability` type owner. | execution/runtime |
| execution_contracts_v1 | infrastructure | PARTIALLY_INTEGRATED | Immutable, provenance-bearing data shapes for the full governed execution lifecycle. | execution/runtime |
| execution_spine | execution | PARTIALLY_INTEGRATED | LEGACY synchronous ExecutionSpine (.run); superseded by canonical spine.py (.execute). | execution/spine.py (canonical) |
| live_local_runtime_execution_v1 | execution | PARTIALLY_INTEGRATED | Single entry point dispatching governed work to local runtime (Discord→governance→WorkPacket→local GUI). | execution/runtime |
| local_runtime_supervisor_v1 | recovery | PARTIALLY_INTEGRATED | Persistent supervisor: watches dispatch queue, manages worker lifecycle, heartbeat, recovery. | execution/runtime |
| node_sync_gate_v1 | governance | PARTIALLY_INTEGRATED | Mandatory VPS↔local code-parity gate (git hash, relay version) before any local execution. | execution/runtime |
| runtime_bootstrap_state_v1 | infrastructure | PARTIALLY_INTEGRATED | Bootstraps runtime dirs/proof folders/config markers/registry caches. | execution/runtime |
| runtime_dispatch_queue_v1 | infrastructure | PARTIALLY_INTEGRATED | Filesystem dispatch queue for WorkPackets with idempotent dedup (VPS enqueue, local dequeue). | execution/runtime |
| runtime_execution_result_v1 | infrastructure | PARTIALLY_INTEGRATED | Proof-bearing structured result type from local supervisor execution. | execution/runtime |
| runtime_heartbeat_v1 | perception | PARTIALLY_INTEGRATED | Persistent worker heartbeat with timeout detection + health-state transitions. | execution/runtime |
| runtime_presence_state_v1 | world-model | PARTIALLY_INTEGRATED | Workstation presence tracking (available/active/executing/disconnected) to gate execution. | execution/runtime |
| runtime_recovery_v1 | recovery | PARTIALLY_INTEGRATED | Structured recovery for worker crash/timeout/adapter failure under governance. | execution/runtime |
| runtime_session_registry_v1 | infrastructure | PARTIALLY_INTEGRATED | Source-of-truth registry binding worker↔environment for active runtime sessions. | execution/runtime |
| substrate_continuity_engine_v1 | learning | PARTIALLY_INTEGRATED | Longitudinal continuity engine consuming traces/outcomes/governance; observe+persist only. | execution/runtime |
| worker_runtime_contracts | infrastructure | PRODUCTION_ACTIVE | Canonical typed descriptors: EnvironmentType, AuthorityDomain (registered in type-coherence law). | execution/runtime |
| worker_supervisor_v1 | recovery | PARTIALLY_INTEGRATED | Autonomous worker lifecycle: health checks, autostart policy, structured remediation. | execution/runtime |
| workpacket_execution_gate_v1 | governance | PARTIALLY_INTEGRATED | Final structural gate (12+ checks) between approved work and real actuation. | execution/runtime |

*The `*_v1` runtime family composes the local-workstation execution spine, reachable via `transports/discord/spine_integration_v1.py`. This is a coherent, mostly-integrated subsystem but not exercised by an always-on service tick → PARTIALLY_INTEGRATED.*

### execution/voice/ (2 modules)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| session | execution | PRODUCTION_ACTIVE | End-to-end voice pipeline loop (audio→VAD→STT→classify→submit→TTS). | execution/voice |
| voice_engine | perception | PRODUCTION_ACTIVE | Discord-specific real-time voice engine (STT/VAD/classify/TTS/local-LLM routing). | execution/voice |

### execution/workers/workstation/ (9 modules)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| environment_mapping_engine_v1 | perception | PARTIALLY_INTEGRATED | Explore→map→classify→plan→ingest engine for the founder workstation environment (never blind-ingest). | execution/workers/workstation |
| foreground_cu_ingestion_execution_v1 | execution | PARTIALLY_INTEGRATED | VPS-side orchestrator for real foreground Computer-Use ingestion via Windows relay. | execution/workers/workstation |
| relay_execution_transport_v1 | infrastructure | PARTIALLY_INTEGRATED | VPS→Windows relay transport (SSH/SCP→WSL→shared FS inbox/outbox polling). | execution/workers/workstation |
| tmux_operational_adapter_v1 | execution | PARTIALLY_INTEGRATED | Governed tmux inspection/session-create/send-command adapter (no shell escalation). | execution/workers/workstation |
| visible_actuation_proof_v1 | reflection | PARTIALLY_INTEGRATED | Classifies relay results into maturity-aware proof (L1 requires real PID+HWND+screenshot+confirm). | execution/workers/workstation |
| workstation_contracts_v1 | infrastructure | PARTIALLY_INTEGRATED | Immutable workstation-state data shapes (session/environment/continuity/resume snapshots). | execution/workers/workstation |
| workstation_execution_orchestrator_v1 | execution | PARTIALLY_INTEGRATED | Sole coordinator of workstation execution through governed pipeline (no direct adapter calls). | execution/workers/workstation |
| workstation_node_registry_v1 | infrastructure | PARTIALLY_INTEGRATED | Tracks known workstation relay nodes for the control plane (currently single-node). | execution/workers/workstation |
| workstation_relay_self_heal_v1 | recovery | PARTIALLY_INTEGRATED | VPS-side relay health assessment + self-heal (heartbeat staleness, autostart state). | execution/workers/workstation |

*Reachable via `transports/api/workstation.py`, `transports/presence/handlers/substrate_command_handler.py`, `transports/discord/interface_adapter_v1.py`. Real-hardware path, integrated but not service-tick-driven.*

### execution/ (root, 8 modules)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| cpu_gate | governance | PRODUCTION_ACTIVE | Single CPU choke-point (gated_subprocess_run/gated_popen); NON-NEGOTIABLE law enforcement. | execution/ |
| credential_gate | governance | PRODUCTION_ACTIVE | Single credential choke-point validating all computer-use creds flow through 1Password. | execution/ |
| executor | execution | PRODUCTION_ACTIVE | Core executor — the only component allowed to act. | execution/ |
| feedback | learning | PRODUCTION_ACTIVE | Implicit quality scoring from execution outcomes → learning loop. | execution/ |
| feedback_loop | learning | PRODUCTION_ACTIVE | Explicit RLHF human feedback ingestion (thumbs/ratings) aggregated for routing. | execution/ |
| mastery_gate | governance | PRODUCTION_ACTIVE | Gates execution on tool-mastery availability (TME enforcement). | execution/ |
| pipeline | execution | PRODUCTION_ACTIVE | Core execution pipeline. | execution/ |
| proof_generator | reflection | PRODUCTION_ACTIVE | Generates execution proofs/evidence artifacts. | execution/ |
| queue | execution | PRODUCTION_ACTIVE | Priority-aware WorkPacket queue (uses canonical WorkPacketPriority). | execution/ |
| spine | execution | PRODUCTION_ACTIVE | **Canonical** async ExecutionSpine — 8-stage governed execution pipeline. | execution/spine.py |
| trace | reflection | PRODUCTION_ACTIVE | Trace recording + Neon persistence. | execution/ |
| understanding_bridge | understanding | PRODUCTION_ACTIVE | Bridges understanding layer into execution. | execution/ |

---

## substrate/control_plane/ (58 modules)

### control_plane/actions/ (11 modules)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| actions | governance | PRODUCTION_ACTIVE | Canonical Action object — unit of control (propose→validate→approve→execute→log). | control_plane/actions |
| control_plane | governance | PRODUCTION_ACTIVE | Public entry point for the Action System lifecycle + deferred/idempotent handling. | control_plane/actions |
| deferred | governance | PRODUCTION_ACTIVE | Durable one-file-per-action persistence for deferred (medium/high-risk) actions. | control_plane/actions |
| deferred_status | governance | PRODUCTION_ACTIVE | Sidecar status tracking (pending/acknowledged/snoozed/stale) for deferred actions. | control_plane/actions |
| executor | execution | PRODUCTION_ACTIVE | Action executors dispatched by action.type; failures captured not raised. | control_plane/actions |
| idempotency | governance | PRODUCTION_ACTIVE | Filesystem O_EXCL sentinel store — exactly-one-execution-per-key within TTL. | control_plane/actions |
| logging | reflection | PRODUCTION_ACTIVE | Append-only JSONL execution + decision loggers. | control_plane/actions |
| notifier | infrastructure | PRODUCTION_ACTIVE | File + Discord notifiers for deferred-action announcements. | control_plane/actions |
| policy | governance | PRODUCTION_ACTIVE | Adapter between runtime-action (lowercase) and business-action (uppercase) governance vocabularies. | control_plane/actions |
| tme | learning | PRODUCTION_ACTIVE | Tool-Mastery-Engine integration: advisory skill search + active mastery assurance. | control_plane/actions |
| validator | governance | PRODUCTION_ACTIVE | Action well-formedness + approval rules. | control_plane/actions |

*Reachable via orchestrator, mastery/research/ensure chains. Distinct runtime-action governance vs the business-action AuthorityEngine — see conflicts.*

### control_plane/agents/ (6 modules)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| agent_hierarchy | governance | PRODUCTION_ACTIVE | Reporting hierarchy (Developer→CEO, EA→CEO→founder). | control_plane/agents |
| agent_teams | coordination | PRODUCTION_ACTIVE | Team composition and membership. | control_plane/agents |
| ceo_agent | reasoning | PRODUCTION_ACTIVE | CEO strategic agent (always best model). | control_plane/agents |
| ceo_intelligence | reasoning | PRODUCTION_ACTIVE | CEO-level intelligence/analysis logic. | control_plane/agents |
| ceo_operational_standards | governance | PRODUCTION_ACTIVE | CEO behavioral/operational standards. | control_plane/agents |
| ea_operational_standards | governance | PRODUCTION_ACTIVE | EA behavioral/operational standards. | control_plane/agents |

### control_plane/context/ (2 modules)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| context_builder | memory | PRODUCTION_ACTIVE | Assembles unified execution context. | control_plane/context |
| context_compaction | memory | PRODUCTION_ACTIVE | Compacts context when approaching limits. | control_plane/context |

### control_plane/coordination/ (1 module)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| coordination_engine | coordination | PRODUCTION_ACTIVE | Cross-agent coordination engine. | control_plane/coordination |

### control_plane/delegation/ (1 module)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| delegation_tracker | coordination | PRODUCTION_ACTIVE | Tracks delegated work across agents. | control_plane/delegation |

### control_plane/events/ (2 modules)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| event_bus | infrastructure | PRODUCTION_ACTIVE | In-process event bus. | control_plane/events |
| event_manager | planning | PRODUCTION_ACTIVE | Manages multi-day/multi-stakeholder events (conferences, offsites) — distinct from calendar. | control_plane/events |

*event_manager reachable via services/discord_bot_commands.py.*

### control_plane/goals/ (1 module)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| goal_selector | planning | PRODUCTION_ACTIVE | Selects next goal deterministically. | control_plane/goals |

### control_plane/identity/ (1 module)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| ai_identity | self-model | PRODUCTION_ACTIVE | AI identity resolution (get_ai_name backing). | control_plane/identity |

### control_plane/invariants/ (3 modules)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| coherence_gate | governance | PARTIALLY_INTEGRATED | Fail-closed gate blocking any packet lacking a valid CoherenceEnvelope from the canonical spine. | control_plane/invariants |
| spine_coherence_validator | governance | PARTIALLY_INTEGRATED | Validates a CoherenceEnvelope represents complete lineage through the 15-stage spine. | control_plane/invariants |
| spine_lineage_contracts | infrastructure | PARTIALLY_INTEGRATED | Typed contracts for the 15-stage canonical spine lineage; packet-as-downstream-artifact model. | control_plane/invariants |

*Reachable only via organism self_use/leverage + `scripts/validate_w0_coherence_dry.py` — proof/certification path, not the live execution hot path → PARTIALLY_INTEGRATED. High architectural value (this is the coherence-by-default enforcement); should be PROMOTED onto the live spine.*

### control_plane/onboarding/ (2 modules)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| onboarding_engine | infrastructure | PRODUCTION_ACTIVE | New-instance onboarding flow. | control_plane/onboarding |
| setup_wizard | infrastructure | PRODUCTION_ACTIVE | Interactive setup wizard. | control_plane/onboarding |

### control_plane/orchestrator/ (1 module)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| orchestrator | coordination | PRODUCTION_ACTIVE | Top-level orchestrator (distinct from runtime/orchestrator/ workflow dispatcher). | control_plane/orchestrator |

### control_plane/proactive/ (1 module)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| proactive_engine | prediction | PRODUCTION_ACTIVE | Proactively surfaces actions/suggestions. | control_plane/proactive |

### control_plane/router/ (3 modules)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| control_plane_router_v1 | reasoning | PARTIALLY_INTEGRATED | Deterministic stateless WorkPacket router (validate→resolve capability→select adapter→delegate). | control_plane/router |
| intent_router | reasoning | PRODUCTION_ACTIVE | Routes signals by detected intent. | control_plane/router |
| router_contracts | infrastructure | PARTIALLY_INTEGRATED | Typed routing-lifecycle dataclasses (RouterWorkPacket/CapabilityRequirement/RouterDecision/RouterResult). | control_plane/router |

*control_plane_router_v1 + router_contracts reachable via transports/presence + transports/discord. Coexists with intent_router (different granularity — see conflicts).*

### control_plane/runtime/ (12 modules — includes runtime/orchestrator/ subpackage)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| runtime/cognitive_loop | reasoning | PRODUCTION_ACTIVE | Core cognitive loop (perceive→reason→act). | control_plane/runtime |
| runtime/gateway | infrastructure | PRODUCTION_ACTIVE | Internal Gateway (context enrichment, agent routing, cognitive loop, quality gates). | control_plane/runtime |
| runtime/substrate_gateway | infrastructure | PRODUCTION_ACTIVE | Public SignalEnvelope→ExecutionResult facade over internal Gateway (transport entry point). | control_plane/runtime |
| runtime/orchestrator/decisions | reasoning | PARTIALLY_INTEGRATED | Deterministic predicates: should_retry/should_escalate/should_ignore for actions. | control_plane/runtime/orchestrator |
| runtime/orchestrator/handlers | execution | PARTIALLY_INTEGRATED | Signal-handler workflows (side effects only via run_action). | control_plane/runtime/orchestrator |
| runtime/orchestrator/loop | coordination | PARTIALLY_INTEGRATED | Autonomous 4-step cycle (drain signals, scan stale deferrals, retry/escalate failures). | control_plane/runtime/orchestrator |
| runtime/orchestrator/orchestrator | coordination | PARTIALLY_INTEGRATED | Thin workflow registry+dispatcher (register_workflow/run_workflow); not a scheduler. | control_plane/runtime/orchestrator |
| runtime/orchestrator/pipeline | execution | PARTIALLY_INTEGRATED | Sequential composition of Control-Plane actions (ActionStep/FuncStep, shared context). | control_plane/runtime/orchestrator |
| runtime/orchestrator/signals | infrastructure | PARTIALLY_INTEGRATED | Filesystem durable-mailbox signal layer (pending/processed dirs, no broker). | control_plane/runtime/orchestrator |
| runtime/orchestrator/steps | execution | PARTIALLY_INTEGRATED | Reusable step helpers extracting the morning/nightly/weekly workflow boilerplate. | control_plane/runtime/orchestrator |
| runtime/orchestrator/workflows | coordination | PARTIALLY_INTEGRATED | Registry wiring the 3 migrated CP workflows + signal bindings (idempotent). | control_plane/runtime/orchestrator |

*The runtime/orchestrator/ subpackage is reachable via `scripts/orchestrator.py`, `scripts/orchestrator_loop.py`, `services/discord_bot.py`. It's a coherent deterministic autonomous-loop subsystem, driven by scripts/cron rather than an always-on Docker tick → PARTIALLY_INTEGRATED.*

### control_plane/scheduling/ (4 modules)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| daily_sync | planning | PRODUCTION_ACTIVE | Daily sync workflow. | control_plane/scheduling |
| ideal_week | planning | PRODUCTION_ACTIVE | Ideal-week template. | control_plane/scheduling |
| personal_admin | planning | PRODUCTION_ACTIVE | Personal admin scheduling. | control_plane/scheduling |
| week_architect | planning | PRODUCTION_ACTIVE | Designs upcoming week from ideal-week template overlaid with real calendar. | control_plane/scheduling |

*week_architect reachable via ideal_week + discord_bot_commands.*

### control_plane/signals/ (1 module)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| signal_hierarchy | understanding | PRODUCTION_ACTIVE | Signal type hierarchy/classification. | control_plane/signals |

### control_plane/strategy/ (4 modules)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| portfolio_advisor | reasoning | PRODUCTION_ACTIVE | Advises across venture portfolio. | control_plane/strategy |
| portfolio_advisor_standards | governance | PRODUCTION_ACTIVE | Standards for portfolio advice. | control_plane/strategy |
| strategy_engine | reasoning | PRODUCTION_ACTIVE | Core strategy reasoning. | control_plane/strategy |
| task_yield_matrix | reasoning | PRODUCTION_ACTIVE | Ranks tasks by yield (leverage math). | control_plane/strategy |

### control_plane/ (root, 3 modules)
| Module | Capability | Status | Unique Contribution | Canonical Owner |
|--------|-----------|--------|--------------------|-----------------|
| governance | governance | PRODUCTION_ACTIVE | Single 5-layer governance facade (signal/business/capability/quality/tier) — exported by substrate API. | control_plane/governance.py |
| memory | memory | PRODUCTION_ACTIVE | Unified MemorySystem protocol wrapping AgentMemory + ConversationMemory — exported by substrate API. | control_plane/memory.py |
| registry | infrastructure | PRODUCTION_ACTIVE | ComponentRegistry (in-memory + Neon-backed) for all substrate components — exported by substrate API. | control_plane/registry.py |

---

## Convergence Recommendations

### MERGE (duplicate capabilities → one canonical owner)

1. **Two ExecutionSpines** → keep canonical `execution/spine.py` (async `.execute()`), archive `execution/runtime/execution_spine.py` (legacy sync `.run()`). The legacy version's header explicitly says "New code should use the canonical version," yet it's still imported by `services/operator_api.py`, `transports/api/operator.py`, and `control_plane/runtime/gateway.py`. Migrate those callers, then archive.

2. **Two feedback modules** → `execution/feedback.py` (implicit quality scoring) and `execution/feedback_loop.py` (explicit RLHF). These are complementary, not duplicate, but both write to overlapping outcomes tables. Consolidate persistence under one owner (`feedback.py`) with `feedback_loop.py` as the explicit-input front-end.

3. **Two capability routers** → `execution/runtime/capability_router.py` (intent→tool, canonical `Capability` type) vs `control_plane/router/control_plane_router_v1.py` (WorkPacket→adapter). Different layers/granularity but overlapping "route to capability" language. Keep both; rename to disambiguate (`tool_capability_router` vs `workpacket_adapter_router`) to prevent future collision.

4. **Two orchestrators inside control_plane** → `control_plane/orchestrator/orchestrator.py` and `control_plane/runtime/orchestrator/orchestrator.py` share a name. The runtime one is a workflow dispatcher; the top-level one is the agent orchestrator. Rename the runtime one to `workflow_dispatcher` — the name clash is a real trap.

5. **Two intent routers** → `control_plane/router/intent_router.py` (signal→intent) vs `control_plane/runtime/orchestrator/decisions.py` (action→retry/escalate/ignore). The `decisions.py` header admits its rules "intentionally mirror the ones in core.orchestrator.loop." Centralize the retry/escalate policy in one module rather than mirroring.

### PROMOTE (dormant but unique value)

1. **execution/agents/computer_use_agent.py** (DORMANT, no runtime importer) — the governed screenshot→vision→gate→act loop. This IS the intended computer-use spine per the Computer Use Law. Wire it into the workstation orchestrator path. Highest-value promotion.

2. **control_plane/invariants/ (coherence_gate + validator + lineage contracts)** — fail-closed coherence enforcement is exactly the "Coherence By Default" principle in memory, but it's only exercised by proof/dry-run scripts today. Promote the gate onto the live execution spine so every packet must prove canonical lineage.

3. **execution/adapters/physical.py** (DORMANT, zero importers) — clean physical/IoT extension-point framework. No current hardware, but it's the documented growth path. Either PROMOTE (register into the adapter registry as a discovery scan) or ARCHIVE until hardware exists — do not leave as orphan scaffolding.

4. **execution/loop/execution_loop.py** (PARTIALLY_INTEGRATED, only canonical_types references it) — the closed goal→execute→outcome loop. Superseded in practice by `persistent_loop.py` + `stages.py`. Either fold its "only Executor acts" invariant into persistent_loop or archive.

### ARCHIVE (superseded, no unique value)

1. **execution/runtime/execution_spine.py** — legacy sync spine, self-documented as superseded. Archive after migrating its 4 callers to `execution/spine.py`.

2. **execution/bridge/discord_output_policy.py** (DORMANT) — 15-line display-name string helper with no importers. Trivial; fold into whatever watcher formats names, or delete.

3. **execution/loop/execution_loop.py** — see PROMOTE #4; if its invariant is already covered by persistent_loop, archive.

### Key Conflicts

1. **Reachability model disagreement (structural).** The narrow reachability set marked ~90 of these 179 modules DORMANT/OBSOLETE. Direct importer analysis shows the vast majority are reachable through `transports/api/*`, `transports/presence/*`, `transports/discord/*`, and `scripts/`. The conflict is definitional: "reachable from a running Docker service tick" (narrow) vs "reachable from any real entry point" (broad). Recommend the census adopt the broad definition and reserve DORMANT strictly for modules with **zero importers** (physical, computer_use_agent, discord_output_policy).

2. **The entire `*_v1` local-runtime + workstation subsystem (26 modules across execution/runtime + execution/workers/workstation)** is a single coherent computer-use execution spine that is fully built, typed, and reachable via transports — but not exercised by an always-on service. It is the largest block of PARTIALLY_INTEGRATED value in the codebase. Convergence decision needed: is this the future execution path (→ wire a live tick and PROMOTE the whole block) or superseded (→ ARCHIVE the block)? It should not stay in limbo.

3. **Dual governance vocabularies** — `control_plane/actions/policy.py` explicitly bridges runtime-action governance (lowercase low/medium/high, disk-persisted deferrals) against business-action governance (uppercase LOW/MEDIUM/HIGH/CRITICAL, Neon-persisted approvals in AuthorityEngine). The bridge is intentional and well-reasoned (avoids circular dep), but two risk vocabularies is a standing coherence hazard. Canonical `RiskClass` in `substrate/types.py` should be the single vocabulary both map to.

4. **Name collisions that will cause real mistakes:** `orchestrator.py` (×2 in control_plane), `capability_router` (execution vs control_plane), `execution_spine`/`spine` (legacy vs canonical), `intent_router` vs `decisions.py` retry logic. Each is a documented trap where a developer imports the wrong one. Disambiguate by rename during convergence.
