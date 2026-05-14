# Transport __init__.py Rewrite — Unblock Inventory
# Date: 2026-05-14

## What changed

`runtime/transport/__init__.py` rewritten from 576-line eager-import
to PEP 562 `__getattr__` lazy-import pattern.

- Before: 40 submodules loaded on `import runtime.transport`
- After: 0 submodules loaded until first attribute access
- Public API surface: unchanged (all symbols still resolve)
- Tests: 94/94 (unchanged)

## Reachability audit (163 modules)

| Category | Count | Status |
|----------|-------|--------|
| Production reachable | 16 | STILL BLOCKED — need import path migration |
| Script-only reachable | 39 | NOW MOVABLE — no production dependency |
| Test-only reachable | 4 | NOW MOVABLE — test imports only |
| Migration-script only | 2 | NOW MOVABLE — codegen tool, not runtime |
| Orphan (in `__init__.py`, no consumer) | 31 | NOW MOVABLE — archive + remove from init |
| Orphan (completely invisible) | 72 | NOW MOVABLE — safe to archive immediately |
| **Total** | **163** | |

## NOW MOVABLE: 148 modules

### Orphan — completely invisible (72 modules)
Safest to archive. Zero external imports. Not in `__init__.py`.

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
`work_order_dispatch`, `work_order_factory`,
`worker_node_contracts`, `worker_node_runtime`

### Orphan — in `__init__.py` but no external consumer (31 modules)
Archive + remove `_m()`/`_d()` registrations from `__init__.py`.

`app_allowlist`, `auto_task_generation`, `capabilities`,
`capability_routing`, `decision_engine`, `event_scheduler`,
`execution_adapter`, `execution_authority`, `execution_contract`,
`execution_events`, `execution_result_handler`, `execution_router`,
`execution_worker`, `live_sessions`, `llm_decision_events`,
`llm_replay`, `local_control`, `perception`,
`pipeline_execution`, `planner`, `role_resolver`, `roles`,
`scenes`, `station_presence`, `station_triggers`,
`task_decomposition`, `task_execution`, `task_pipeline`,
`task_queue`, `task_system`, `voice_wake`

### Script-only reachable (39 modules)
Imported by `scripts/` only (smoke tests, diagnostics). Movable.

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

### Test-only reachable (4 modules)
Imported only by `tests/`. Movable.

`instance_ingestion_contracts`, `local_worker_auto_loop`,
`local_worker_runtime_daemon`, `write_founder_gate_confirmation`

### Migration-script only (2 modules)
Referenced by `scripts/r8d_generate_shims.py` (codegen, not runtime).

`llm_planner`, `work_order_contracts`

## STILL BLOCKED: 16 production-reachable modules

These are imported by live services or production runtime code.
They cannot be archived — they need import path migration to §24 homes.

| Module | Production importer(s) |
|--------|----------------------|
| `capability_tagging` | `control_plane/runtime/gateway.py` |
| `claude_responder` | `execution/runtime/model_router.py` |
| `day_workflows` | `services/discord_bot.py` (via substrate .pyc) |
| `discord_mode_routing` | `execution/runtime/model_router.py` |
| `discord_text_transport` | `services/discord_bot.py` (via substrate .pyc) |
| `discord_voice_transport` | `services/discord_bot.py` (via substrate .pyc) |
| `event_spine` | `services/discord_bot.py` (via substrate .pyc) |
| `execution_trace` | `execution/runtime/model_router.py` |
| `interaction_archive` | `services/discord_bot.py` (via substrate .pyc) |
| `memory_scope_contracts` | `understanding/perception/orchestrator.py` |
| `session_discord_bridge` | `services/discord_bot.py` (via substrate .pyc) |
| `session_watcher` | `services/discord_bot.py` (via substrate .pyc) |
| `station_daemon` | `services/discord_bot.py` (via substrate .pyc) |
| `station_helpers` | `services/discord_bot.py` (via substrate .pyc) |
| `storage` | `execution/runtime/execution_spine.py`, `runtime/world_model.py` |
| `voice_eos_responder` | `services/discord_bot.py` (via substrate .pyc) |

### Urgent risk: substrate .pyc shim cache

`services/discord_bot.py` imports ~11 transport modules via
`runtime.substrate.*` paths. The source `.py` files in `runtime/substrate/`
were deleted in Wave 6. The bot is running on stale `.pyc` bytecode.

**A Docker rebuild, Python version change, or `__pycache__` cleanup
will crash os-discord.**

Resolution: migrate discord_bot.py substrate imports to direct
`runtime.transport.*` paths before any container rebuild. This is
Row 76 + Row 60 from the triage manifest.

## Recommended execution order

1. **Immediate**: Archive 72 completely invisible orphans (zero risk)
2. **Next**: Archive 31 init-registered orphans + trim `__init__.py`
3. **Next**: Archive 39 script-only modules (update script imports)
4. **Prerequisite for container rebuild**: Migrate discord_bot.py
   substrate imports → direct transport paths (16 production modules)
5. **Future**: Relocate 16 production modules to §24 homes
