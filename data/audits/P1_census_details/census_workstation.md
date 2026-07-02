# Census: substrate/workstation/ (55 modules)

## Production-status method

Four named production entry points: `daemon.py`, `cognitive_loop.py`, `gateway.py`, `discord_bot.py`.

Two production reachability chains found:

1. **discord_bot chain** (PRODUCTION_ACTIVE):
   `discord_bot.py` → `discord_message_handlers._handle_dex_conversation` →
   `dex_conversation` (shim) → `advisor_conversation.py` → imports
   `command_router, voice_route_resolver, vps_control_catalog, continuity,
   lifecycle_modes, continuity_engine, intent_contract, profile_modes,
   profile_behavior, grounded_handlers→camera_commands`.

2. **daemon chain** (PRODUCTION_ACTIVE):
   `daemon.py:85` → `substrate.execution.pipeline:53` → `workstation.state`.

Everything reached only through the cockpit API
(`services/operator_api.py` → `transports.api.cockpit` → `cockpit_*_routes.py`)
is real, wired, and served — but NOT via one of the four named entry points →
classified **PARTIALLY_INTEGRATED**. The cockpit API is a live service; these
are not dead code, they are simply not on the daemon/discord/gateway/loop path.

Vision cluster (`tracker_stack, trigger_chains, vision_presets, vision_privacy,
vision_query, vision_scene, security_mode`) has **zero importers in
substrate/transports/services/adapters**, but IS imported by
`umh/vision_relay.py` — a standalone Beast vision WebSocket server
(`ws://0.0.0.0:8097/vision`, has `async def main()`). So it is a separate
service outside the four entry points → **PARTIALLY_INTEGRATED**, not dormant.

`canonical_types.py` entries are a lazy-import registry (a type-locator table),
not a runtime importer — noted but not counted as a production consumer.

| Module | Capability | Status | Importers | Unique Contribution | Canonical Owner |
|--------|-----------|--------|-----------|-------------------|----------------|
| activation.py | perception | PARTIALLY_INTEGRATED | cockpit_presence_routes | Typed ActivationSignal + PresenceSession contract (manual/hotkey/typed/PTT/Discord sources) | substrate/workstation (presence) |
| agent_workforce_runtime.py | world-model | PARTIALLY_INTEGRATED | cockpit_agent_workforce_routes, production_ops_runtime, production_workforce_runtime | Read-only workforce capacity view: idle/overloaded agents, capability gaps | substrate/workstation (aggregators) |
| ambient_wake_runtime.py | perception | PARTIALLY_INTEGRATED | cockpit_ambient_wake_routes, voice runtimes | DORMANT→PASSIVE→WAKE→COMMAND wake-word state machine | substrate/workstation (voice) |
| app_resolver.py | reasoning | DORMANT | (only intra: camera/voice-adjacent) 2 workstation refs | Deterministic app-vs-website resolution, Chrome-first browser policy | substrate/workstation (resolution) |
| attention_aggregation_runtime.py | perception | PARTIALLY_INTEGRATED | cockpit_attention_routes, attention_vision_runtime | Merges 4 attention sources into one ranked queue | substrate/workstation (attention) |
| attention_vision_runtime.py | perception | PARTIALLY_INTEGRATED | cockpit_visual_attention_routes, visual_operations_runtime | Deterministic visual attention ranking (scans screen for error signals) | substrate/workstation (vision) |
| camera_commands.py | execution | PRODUCTION_ACTIVE | grounded_handlers (→advisor_conversation→discord) | Routes CAMERA_CONTROL intents (PTZ/zoom/track/snapshot) to mesh camera adapter | substrate/workstation (vision) |
| checkpoint.py | memory | PARTIALLY_INTEGRATED | cockpit_workstation_control_routes, cockpit_workspace_routes, continuity_engine | Point-in-time system-state snapshot on continuity transitions | substrate/workstation (continuity) |
| cockpit_capability_map.py | self-model | PARTIALLY_INTEGRATED | cockpit_capability_map_routes | Static audit surface: cockpit routes/panels/stores, duplication + MVP coverage | substrate/workstation (audit) — candidate ARCHIVE |
| command_center_mvp_runtime.py | reflection | PARTIALLY_INTEGRATED | cockpit_command_center_mvp_routes | Composes 10 subsystems into operator landing snapshot (situation/attention/next) | substrate/workstation (composition roots) |
| command_router.py | understanding | PRODUCTION_ACTIVE | advisor_conversation (→discord), cockpit_presence_routes | Deterministic NL→CommandIntent classification + governance routing | substrate/workstation (command) |
| continuity.py | governance | PRODUCTION_ACTIVE | advisor_conversation (→discord), cockpit routes, +6 intra | Continuity state machine composing 4 legacy mode systems | substrate/workstation (continuity) — HUB |
| continuity_engine.py | governance | PRODUCTION_ACTIVE | advisor_conversation (→discord), cockpit_core_bootstrap_routes | Orchestrator binding all continuity subsystems (startup/shutdown/resume) | substrate/workstation (continuity) |
| device_presence.py | perception | PARTIALLY_INTEGRATED | cockpit_core_session_routes, cockpit_presence_routes, presence_runtime, +5 | In-memory registry of connected operator surfaces + mesh reachability | substrate/workstation (presence) — HUB |
| environment_awareness_runtime.py | world-model | PARTIALLY_INTEGRATED | cockpit_visual_environment_routes, visual_operations/context runtimes | Aggregates all observable surfaces (desktop/cockpit/terminal/browser) | substrate/workstation (vision) |
| execution_fabric_runtime.py | world-model | PARTIALLY_INTEGRATED | cockpit_execution_fabric_routes, production_ops_runtime | Composes 6 runtimes: what's running/blocked, capacity remaining | substrate/workstation (aggregators) |
| file_browser.py | infrastructure | PARTIALLY_INTEGRATED | cockpit_workspace_routes, cockpit_core_bootstrap_routes | Safe allowlisted read-only filesystem browser for Meta IDE | substrate/workstation (io) |
| intent_contract.py | planning | PRODUCTION_ACTIVE | advisor_conversation (→discord), cockpit routes | Converts operator intent into end-state design (acceptance criteria, autonomy) | substrate/workstation (loop) |
| jarvis_command.py | obsolete | OBSOLETE | none (0) | Backward-compat shim re-exporting command_router | DELETE |
| lifecycle_modes.py | governance | PRODUCTION_ACTIVE | advisor_conversation (→discord), continuity, mode_resolver | System lifecycle modes (DAY/NIGHT/OVERNIGHT/MAINTENANCE) governing risk ceiling | substrate/workstation (modes) |
| loop_engine.py | recovery | PARTIALLY_INTEGRATED | intent_contract (1) + canonical registry | Deterministic end-state verification / loop-completion contracts | substrate/workstation (loop) |
| meta_ide_context_runtime.py | world-model | PARTIALLY_INTEGRATED | cockpit_meta_ide_context_routes, visual_context_runtime, production_ops_runtime | Read-only build-context binding (device/repo/branch/files/goals) | substrate/workstation (meta-ide) |
| meta_ide_projection_loop_runtime.py | planning | PARTIALLY_INTEGRATED | cockpit_meta_ide_projection_loop_routes, operating_loop_runtime | Governed build-from-cockpit loop (intent→plan→dispatch→review→merge) | substrate/workstation (meta-ide) |
| mode_commands.py | understanding | PARTIALLY_INTEGRATED | cockpit_workstation_control_routes (1) | Parses NL mode-switch commands → structured mode change | substrate/workstation (modes) |
| mode_resolver.py | reasoning | PARTIALLY_INTEGRATED | cockpit_workstation_control_routes, cockpit_unified_workstation_routes, cockpit_core_bootstrap_routes | Authoritative composite of all mode systems into one snapshot | substrate/workstation (modes) — HUB |
| mvp_readiness_runtime.py | reflection | PARTIALLY_INTEGRATED | cockpit_mvp_readiness_routes | Objective MVP readiness scoring across 14 dimensions | substrate/workstation (audit) — candidate ARCHIVE |
| operating_loop_runtime.py | reflection | PARTIALLY_INTEGRATED | cockpit_operating_loop_routes | Loop visibility/lineage/tracking layer (NOT an execution engine) | substrate/workstation (loop) |
| orchestrator_presence_runtime.py | self-model | PARTIALLY_INTEGRATED | cockpit_orchestrator_presence_routes, executive_brief_runtime, strategic_context_runtime | Persistent orchestrator presence snapshot composing 8 subsystems | substrate/workstation (presence) |
| overnight_queue.py | planning | PARTIALLY_INTEGRATED | cockpit_workstation_control_routes, cockpit_unified_workstation_routes, cockpit_core_bootstrap_routes | Thin overnight safe-work queue (queue/pause/approval, dry-run only) | substrate/workstation (loop) |
| profile_behavior.py | governance | PRODUCTION_ACTIVE | advisor_conversation (→discord), profile-adjacent | Per-profile voice/camera/notification/app policies | substrate/workstation (modes) |
| profile_modes.py | governance | PRODUCTION_ACTIVE | advisor_conversation (→discord), continuity_runtime, cockpit routes | Operator work/activity profile modes (DEVELOPER/RESEARCH/MUSIC/DESIGN) | substrate/workstation (modes) |
| resume_brief.py | memory | PARTIALLY_INTEGRATED | cockpit_workstation_control_routes, continuity_engine | "What happened while I was gone?" return-brief generator | substrate/workstation (continuity) |
| screen_awareness_runtime.py | perception | PARTIALLY_INTEGRATED | cockpit_visual_awareness_routes, +4 C21 runtimes | Screen state + device-session binding over ScreenObservationEngine | substrate/workstation (vision) — HUB |
| security_mode.py | governance | PARTIALLY_INTEGRATED | umh/vision_relay (service), tests | Governed security-harden posture (elevated gates, safety constraints) | substrate/workstation (vision) |
| session_machine_runtime.py | world-model | PARTIALLY_INTEGRATED | cockpit_session_machine_routes, environment/production_ops runtimes | Binds machine→session→workspace→task into one model | substrate/workstation (aggregators) |
| state.py | memory | PRODUCTION_ACTIVE | pipeline.py (→daemon), transports/api/workstation, cockpit_presence_routes (29 total) | Lightweight workstation runtime snapshot (profile/session/resume) | substrate/workstation (state) — HUB |
| tracker_stack.py | perception | PARTIALLY_INTEGRATED | umh/vision_relay (service), tests | Independent stackable vision trackers (cost/fps/latency, graceful degrade) | substrate/workstation (vision) |
| trigger_chains.py | reasoning | PARTIALLY_INTEGRATED | umh/vision_relay (service), tests | Deterministic vision event→condition→action chains (debounced, governed) | substrate/workstation (vision) |
| unified_approval_runtime.py | governance | PARTIALLY_INTEGRATED | cockpit_unified_approval_routes, governed_execution/work_readiness/production_review runtimes (8) | Single approval queue across 11 subsystems w/ urgency scoring | substrate/workstation (aggregators) — HUB |
| unified_execution_surface_runtime.py | world-model | PARTIALLY_INTEGRATED | cockpit_unified_execution_routes | Merges execution+agents+compute+work+approvals+proof into one stream | substrate/workstation (aggregators) |
| unified_workstation_runtime.py | world-model | PARTIALLY_INTEGRATED | cockpit_unified_workstation_routes | Single source of truth composing 7 runtimes into read-only snapshot | substrate/workstation (composition roots) |
| vision_presets.py | memory | PARTIALLY_INTEGRATED | umh/vision_relay (service), tests | Full CRUD for camera presets (PTZ/ROI/tracker stacks/zones) | substrate/workstation (vision) |
| vision_privacy.py | governance | PARTIALLY_INTEGRATED | umh/vision_relay (service), 4 test files | Hard-coded non-configurable camera-usage privacy constraints | substrate/workstation (vision) |
| vision_query.py | understanding | PARTIALLY_INTEGRATED | umh/vision_relay (service), tests | Grounded visual QA (frame/scene traced, no hallucination) | substrate/workstation (vision) |
| vision_scene.py | world-model | PARTIALLY_INTEGRATED | umh/vision_relay (service), tests | Grounded workspace scene model from camera frames (traced to frame+confidence) | substrate/workstation (vision) |
| visual_context_runtime.py | world-model | PARTIALLY_INTEGRATED | cockpit_visual_context_routes, visual_operations_runtime | Screen→app→repo→branch→file→work-packet→goals context waterfall | substrate/workstation (vision) |
| visual_operations_runtime.py | perception | PARTIALLY_INTEGRATED | cockpit_visual_ops_routes, voice_query_engine | Composition root for all C21 visual sub-runtimes (facade) | substrate/workstation (composition roots) |
| voice_ingress_runtime.py | perception | PARTIALLY_INTEGRATED | cockpit_voice_ingress_routes, cockpit_voice_session_routes, +4 voice runtimes | Classifies/tags every audio event (source/device/speaker/channel) | substrate/workstation (voice) — HUB |
| voice_operations_runtime.py | execution | PARTIALLY_INTEGRATED | cockpit_voice_ops_routes | Composition root: process_utterance() full voice→output pipeline | substrate/workstation (composition roots) |
| voice_output_runtime.py | execution | PARTIALLY_INTEGRATED | cockpit_voice_output_routes, voice_operations_runtime | Static response→output-surface routing (no intelligence) | substrate/workstation (voice) |
| voice_route_resolver.py | reasoning | PRODUCTION_ACTIVE | advisor_conversation (→discord), voice runtimes | Separates execution target from audio output device (deterministic) | substrate/workstation (voice) |
| voice_session_manager.py | governance | PARTIALLY_INTEGRATED | cockpit_voice_session_routes, +4 voice runtimes | Multi-surface voice session lifecycle w/ COMMAND>CONVERSATION>PASSIVE conflict | substrate/workstation (voice) — HUB |
| vps_control_catalog.py | execution | PRODUCTION_ACTIVE | advisor_conversation (→discord) | Governed VPS command catalog (declarative templates, no raw shell) | substrate/workstation (command) |
| work_lane.py | reasoning | PARTIALLY_INTEGRATED | (1 intra ref) | Multi-session lane routing + foreground guard (deterministic) | substrate/workstation (command) |
| workstation_presence_runtime.py | self-model | PARTIALLY_INTEGRATED | cockpit_workstation_presence_routes, orchestrator_presence_runtime | Operator footprint (device/panel/project/last action), ephemeral | substrate/workstation (presence) |

## Convergence Recommendations

### MERGE
- **jarvis_command.py → command_router.py**: pure re-export shim, 0 importers. Also `dex_conversation.py` (organism-layer shim) points here conceptually — `advisor_conversation` is the canonical name.
- **Presence cluster** (activation, device_presence, workstation_presence_runtime, orchestrator_presence_runtime): four overlapping "who/where is the operator" surfaces. `device_presence` is the registry HUB; the three runtimes are read-only compositions over it. Fold into a single `presence/` subpackage with device_presence as the sole state owner.
- **Aggregator/composition-root cluster** (unified_workstation_runtime, unified_execution_surface_runtime, execution_fabric_runtime, agent_workforce_runtime, session_machine_runtime, command_center_mvp_runtime): six read-only "compose N runtimes into one snapshot" modules, all PARTIALLY_INTEGRATED via one cockpit route each. Strong overlap in aggregate→normalize→present pattern. Merge into a `workstation/aggregators/` subpackage with a shared snapshot base to kill boilerplate.
- **Vision runtime cluster** (screen_awareness, environment_awareness, attention_vision, visual_context, visual_operations): C21 chain where visual_operations_runtime is already the facade. Collapse the sub-runtimes behind that single facade; expose one `visual_operations/` subpackage.
- **Voice cluster** (voice_ingress, voice_session_manager, voice_output, voice_operations, ambient_wake, voice_route_resolver): C20 chain with voice_operations_runtime as facade. Consolidate into `voice/`; voice_route_resolver is the only PRODUCTION_ACTIVE member (via advisor) — keep its interface stable through the merge.

### PROMOTE
- **advisor_conversation cluster to first-class**: continuity, continuity_engine, command_router, voice_route_resolver, vps_control_catalog, intent_contract, lifecycle_modes, profile_modes, profile_behavior, camera_commands are the only PRODUCTION_ACTIVE modules (reached from discord_bot). These are the load-bearing spine of the workstation package — promote them into a stable `workstation/core/` (or command+continuity+modes subpackages) with a published contract, since a live user path depends on them daily.
- **state.py**: PRODUCTION_ACTIVE via the daemon execution pipeline AND has 29 importers — it is the de-facto workstation state hub. Promote to the canonical workstation state owner; ensure nothing else redefines WorkstationProfile.

### ARCHIVE
- **cockpit_capability_map.py** and **mvp_readiness_runtime.py**: static self-audit surfaces seeded from hand-maintained registries ("is UMH the MVP?", "what does the cockpit contain?"). These are campaign-era (C3/C4) introspection artifacts, not runtime capabilities. With the platform frozen at v1.0.0, they drift immediately. Archive unless a live cockpit panel still renders them (only reached by their one route each).
- **Vision-relay-only cluster** if `umh/vision_relay.py` is not a deployed service on the current Beast: tracker_stack, trigger_chains, vision_presets, vision_query, vision_scene, security_mode, vision_privacy have NO importer inside substrate/transports/services — only vision_relay + tests. Confirm vision_relay is actually running; if it is retired, ARCHIVE this whole cluster. (camera_commands stays — it IS production-active via discord.)

### DELETE
- **jarvis_command.py**: 0 importers, pure shim. Safe delete after confirming no dynamic import by string.

### Key Conflicts
1. **Two production entry surfaces, one package.** Only ~11 of 55 modules are reachable from the four named entry points (all via discord_bot→advisor_conversation, plus state.py via daemon). The other ~44 are live only through the cockpit HTTP API (operator_api → transports.api.cockpit). This is not dead code, but the "PRODUCTION_ACTIVE" definition (daemon/loop/gateway/discord only) structurally excludes the entire cockpit-served surface. Convergence must decide whether the cockpit API counts as a production entry point — if yes, ~90% of this package flips to PRODUCTION_ACTIVE.
2. **1:1 route-to-runtime coupling.** Nearly every PARTIALLY_INTEGRATED runtime is imported by exactly one `cockpit_*_routes.py` and nothing else. The package is effectively a set of HTTP-endpoint backends, not a reusable substrate library. If a route is retired, its runtime becomes instantly dormant. Ownership should track the route contract.
3. **Facade duplication.** Three "composition root / facade" modules (unified_workstation_runtime, visual_operations_runtime, voice_operations_runtime) plus the six-module aggregator cluster all implement the same aggregate→normalize→present shape independently. High risk of divergent snapshot schemas.
4. **Shim layering.** `dex_conversation` (organism) and `jarvis_command` (workstation) are both backward-compat shims for renamed modules — the canonical names (advisor_conversation, command_router) are the real owners. These shims mask the true production dependency graph.
5. **canonical_types.py registry vs runtime import.** ~120 workstation symbols are registered in canonical_types.py as lazy-import locations. This registry inflates apparent coupling but is not a runtime consumer — convergence tooling that counts registry entries as importers will overcount workstation's reach.
