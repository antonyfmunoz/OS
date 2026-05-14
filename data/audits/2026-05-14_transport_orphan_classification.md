# Transport Orphan Classification — 2026-05-14

Post-Phase-C re-classification of 163 transport modules.
Original inventory: `2026-05-14_transport_unblock_inventory.md`

## Summary

Initial classification (external callers only):

| Category | Count | Action |
|----------|-------|--------|
| TRUE_ORPHAN (not init-registered) | 73 | ARCHIVE immediately |
| TRUE_ORPHAN (init-registered) | 32 | ARCHIVE + remove from `__init__.py` |
| SCRIPT_ONLY callers | 39 | ARCHIVE (callers are smoke tests / diagnostics) |
| TEST_ONLY callers | 4 | ARCHIVE (callers are test files) |
| PROD callers | 15 | DEFER — migrate to §24 in follow-up |
| **Total** | **163** | |

### Post-archive correction

Transitive closure analysis (AST-based) revealed 15 PROD modules
depend on 53 additional modules via intra-transport import chains.
53 modules restored from archive.

| Category | Count | Status |
|----------|-------|--------|
| TRUE_ORPHAN archived | 95 | ARCHIVED (zero deps on remaining modules) |
| INTRA_TRANSPORT (PROD deps) | 53 | RESTORED — move with package |
| PROD callers | 15 | DEFER — migrate to §24 with full package |
| **Total** | **163** | |
| Test files archived | 5 | Tests for archived modules |
| Test method removed | 1 | Imported archived module |

Final archive: 95 transport modules + 5 test files
Remaining in runtime/transport/: 68 .py files (15 PROD + 53 deps)

## TRUE_ORPHAN — not init-registered (73 modules)

Zero external callers. Not in `__init__.py`. Safe to archive immediately.

`adapter_best_practices_loader`, `adapter_engine_contracts`,
`adapter_generation_contracts`, `adapter_quality_gate`,
`advisor_bridge_transport`, `advisor_relay_runtime`,
`advisor_session_contracts`, `approved_action_executor`,
`auth_layer_contracts`, `backend_registry_contracts`,
`backend_selection_engine`, `browser_agent`,
`canonical_source_record`, `capability_routing_contracts`,
`chrome_accessibility_launch_backend`, `chrome_profile_launch_backend`,
`chrome_profile_resolver`, `computer_use_backend_contracts`,
`control_bridge`, `control_commands`,
`cu_document_reader_hardening_plan`, `doc_cu_vs_api_comparator`,
`drive_ui_inventory_comparator`, `environment_contracts`,
`extraction_backend_contracts`, `extraction_parity_comparator`,
`google_docs_backend_parity_matrix`, `google_docs_tab_audit`,
`google_docs_tab_extractor`, `google_workspace_backend_options`,
`governance_gate_contracts`, `gui_backend_healthcheck`,
`interactive_gui_worker_contracts`, `interactive_shell_executor`,
`interface_projection_contracts`, `local_env_secret_backend`,
`local_executor`, `local_gui_control_contracts`,
`local_worker_relay_packets`, `mcp_backend_classifier`,
`mcp_backend_contracts`, `mcp_backend_discovery`,
`meeting_intelligence`, `message_bus_contracts`,
`node_controller`, `node_transport`,
`operator_interface`, `operator_session`,
`os_controller`, `playback_status`,
`remote_identity`, `ritual_inference`,
`scene_capabilities`, `scene_policy`,
`secret_broker_contracts`, `secret_redaction`,
`source_lifecycle_contracts`, `station_readiness`,
`substrate_projection_boundaries`, `template_promotion_contracts`,
`tmux_environment_manager`, `topology_contracts`,
`visible_browser_launch_backend`, `visible_drive_ui_inventory`,
`visible_google_doc_reader`, `visible_gui_success_criteria`,
`windows_desktop_relay_client`, `windows_user_session_launcher`,
`work_order_contracts`, `work_order_dispatch`,
`work_order_factory`, `worker_node_contracts`,
`worker_node_runtime`

## TRUE_ORPHAN — init-registered (32 modules)

Zero external callers. Registered in `__init__.py` via `_m()` or `_d()`.
Archive + remove registrations from init.

`app_allowlist`, `auto_task_generation`, `capabilities`,
`capability_routing`, `decision_engine`, `event_scheduler`,
`execution_adapter`, `execution_authority`, `execution_contract`,
`execution_events`, `execution_result_handler`, `execution_router`,
`execution_worker`, `live_sessions`, `llm_decision_events`,
`llm_planner`, `llm_replay`, `local_control`, `perception`,
`pipeline_execution`, `planner`, `role_resolver`, `roles`,
`scenes`, `station_presence`, `station_triggers`,
`task_decomposition`, `task_execution`, `task_pipeline`,
`task_queue`, `task_system`, `voice_wake`

Also registered but orphan (deferred group, 13 of 32):
`decision_engine`, `event_scheduler`, `execution_adapter`,
`execution_authority`, `execution_contract`, `execution_events`,
`execution_result_handler`, `execution_router`, `execution_worker`,
`llm_decision_events`, `llm_planner`, `llm_replay`, `planner`

## SCRIPT_ONLY callers (39 modules)

External callers only in `scripts/` (smoke tests, diagnostics).
These scripts are non-production — safe to archive the transport
modules. Script references will become stale (expected).

`actions`, `audio_loop`, `claude_session_bridge`, `context_lifecycle`,
`discord_voice_playback`, `google_meet_source`, `local_listener`,
`meet_caption_bridge`, `meeting_sources`, `meeting_transport`,
`mode_behavior`, `nodes`, `operator_presence`, `operator_state`,
`operator_transitions`, `ptt_binding`, `remote_executor`,
`resource_guard`, `result_query`, `result_store`,
`ritual_body`, `ritual_reconciler`, `ritual_runner`, `rituals`,
`session_control`, `session_orchestration`, `station`, `station_bus`,
`station_drainer`, `stt_producer`, `target_policy`,
`transcript_inject`, `transport_report`, `tts_sanitize`,
`voice_session`, `wake_producer`, `workflow_delegation`,
`workflow_execution`, `workload_policy`

## TEST_ONLY callers (4 modules)

External callers only in `tests/`.

`instance_ingestion_contracts`, `local_worker_auto_loop`,
`local_worker_runtime_daemon`, `write_founder_gate_confirmation`

## MIGRATION CANDIDATES — PROD callers (15 modules)

External callers in production code. Defer to §24 migration follow-up.

| Module | Ext callers | Production importers |
|--------|-------------|---------------------|
| `capability_tagging` | 1 | `control_plane/runtime/gateway.py` |
| `claude_responder` | 5 | `execution/runtime/model_router.py` + 4 scripts |
| `day_workflows` | 1 | `services/discord_bot.py` |
| `discord_mode_routing` | 5 | `interface/presence/handlers/intent_handler.py`, `services/discord_bot.py`, `execution/runtime/model_router.py` + 2 scripts |
| `discord_text_transport` | 7 | `services/discord_bot.py` + 6 scripts |
| `discord_voice_transport` | 7 | `services/discord_bot.py` + 6 scripts |
| `event_spine` | 1 | `services/discord_bot.py` |
| `execution_trace` | 6 | `execution/runtime/model_router.py` + 5 scripts |
| `memory_scope_contracts` | 3 | `understanding/perception/orchestrator.py` + 2 scripts |
| `session_discord_bridge` | 4 | `services/discord_bot.py` + 3 scripts |
| `session_watcher` | 5 | `services/discord_bot.py` + 4 scripts |
| `station_daemon` | 19 | `services/discord_bot.py` + scripts |
| `station_helpers` | 7 | `services/discord_bot.py` + scripts |
| `storage` | 5 | `execution/runtime/execution_spine.py`, `understanding/world_model/world_model.py`, `interface/presence/handlers/intent_handler.py`, `services/discord_bot.py` + scripts |
| `voice_eos_responder` | 4 | `services/discord_bot.py` + scripts |

### Registered modules in PROD category (keep in `__init__.py`)

11 modules: `actions`, `capability_tagging`, `nodes`, `ritual_body`,
`rituals`, `station`, `station_bus`, `station_daemon`,
`station_helpers`, `storage`, `voice_session`

Note: `actions`, `nodes`, `ritual_body`, `rituals`, `station`,
`station_bus`, `voice_session` are SCRIPT_ONLY but init-registered.
Keep in init until package migration.
