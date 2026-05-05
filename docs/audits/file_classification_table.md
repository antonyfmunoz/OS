# UMH File Classification Table

**Date:** 2026-04-26
**Total files:** 529
**CORE:** 70 | **MVP:** 177 | **FUTURE:** 269 | **DELETE_CANDIDATE:** 13 | **REFACTOR_LATER:** 5

---

## (root)/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **CORE** |  |
| `__main__.py` | **CORE** |  |
| `run.py` | **CORE** |  |

## actions/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **FUTURE** |  |
| `channel.py` | **FUTURE** |  |
| `router.py` | **FUTURE** |  |
| `schema.py` | **FUTURE** |  |

## adapters/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **CORE** |  |
| `base.py` | **CORE** |  |
| `bridge.py` | **CORE** |  |
| `contracts.py` | **CORE** |  |
| `discord_adapter.py` | **FUTURE** |  |
| `event_router.py` | **CORE** |  |
| `llm.py` | **CORE** |  |
| `model_router.py` | **CORE** |  |
| `notion_adapter.py` | **FUTURE** |  |
| `null.py` | **DELETE_CANDIDATE** |  |
| `provider_health.py` | **MVP** |  |
| `registry.py` | **CORE** |  |
| `stt_engine.py` | **FUTURE** |  |
| `stubs.py` | **MVP** |  |
| `tts_engine.py` | **FUTURE** |  |
| `umh_goals.py` | **FUTURE** |  |
| `umh_storage.py` | **MVP** |  |
| `umh_strategy.py` | **FUTURE** |  |
| `voice_adapter.py` | **FUTURE** |  |
| `voice_loop.py` | **FUTURE** |  |
| `voice_state.py` | **FUTURE** |  |
| `workstation_adapter.py` | **DELETE_CANDIDATE** |  |

## adapters/execution/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **CORE** |  |
| `batch_drainer.py` | **FUTURE** |  |
| `execution_bridge.py` | **FUTURE** |  |
| `workstation_adapter.py` | **FUTURE** |  |

## analytics/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **FUTURE** |  |
| `adaptive_exploration.py` | **FUTURE** |  |
| `exploration_engine.py` | **FUTURE** |  |
| `fabric_analytics.py` | **FUTURE** |  |
| `pattern_engine.py` | **FUTURE** |  |
| `score_distribution.py` | **FUTURE** |  |
| `signal_orchestrator.py` | **FUTURE** |  |
| `strategy_mutation.py` | **FUTURE** |  |
| `strategy_pattern_memory.py` | **FUTURE** |  |
| `strategy_synthesizer.py` | **FUTURE** |  |

## capability/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **MVP** |  |
| `registry.py` | **MVP** |  |
| `router.py` | **MVP** |  |

## context/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **MVP** |  |
| `budget.py` | **FUTURE** |  |
| `builder.py` | **CORE** |  |
| `types.py` | **CORE** |  |

## core/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **CORE** |  |
| `clock.py` | **CORE** |  |

## decision/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **MVP** |  |
| `trace.py` | **MVP** |  [REFACTOR_LATER] |

## environments/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **MVP** |  |
| `detector.py` | **MVP** |  |
| `system_context.py` | **CORE** |  |

## execution/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **CORE** |  |
| `contract.py` | **CORE** |  |
| `engine.py` | **CORE** |  |
| `harness.py` | **CORE** |  |
| `interfaces.py` | **CORE** |  |
| `pipeline.py` | **CORE** |  |
| `quality.py` | **CORE** |  |
| `runtime.py` | **CORE** |  |
| `stages.py` | **CORE** |  |
| `system_graph.py` | **DELETE_CANDIDATE** |  |
| `system_registry.py` | **DELETE_CANDIDATE** |  |
| `system_selector.py` | **DELETE_CANDIDATE** |  |

## feedback/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **MVP** |  |
| `dynamics.py` | **FUTURE** |  |
| `loop.py` | **MVP** |  |
| `outcome_evaluator.py` | **MVP** |  |
| `outcome_feedback.py` | **FUTURE** |  |

## gateway/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **CORE** |  |
| `entry.py` | **CORE** |  |

## goals/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **MVP** |  |
| `alignment.py` | **FUTURE** |  |
| `arbitrator.py` | **FUTURE** |  |
| `budget.py` | **FUTURE** |  |
| `credit.py` | **FUTURE** |  |
| `engine.py` | **FUTURE** |  |
| `evaluator.py` | **FUTURE** |  |
| `interfaces.py` | **FUTURE** |  |
| `meta_goal.py` | **FUTURE** |  |
| `mode.py` | **FUTURE** |  |
| `objective.py` | **FUTURE** |  |
| `state.py` | **MVP** |  |
| `validator.py` | **FUTURE** |  |

## governance/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **MVP** |  |
| `authority.py` | **CORE** |  |
| `capability.py` | **MVP** |  |
| `governor.py` | **FUTURE** |  |

## intent/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **MVP** |  |
| `compiler.py` | **MVP** |  |
| `compiler_ext.py` | **FUTURE** |  |

## interfaces/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **CORE** |  |
| `cli.py` | **CORE** |  |

## interfaces/discord/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **MVP** |  |
| `bot.py` | **MVP** |  [REFACTOR_LATER] |
| `dm_monitor.py` | **MVP** |  |
| `__init__.py` | **MVP** |  |
| `cc_command_handler.py` | **MVP** |  |
| `intent_handler.py` | **MVP** |  |
| `pipeline_handler.py` | **MVP** |  |
| `voice_handler.py` | **FUTURE** |  |
| `__init__.py` | **MVP** |  |
| `attachment_fallback.py` | **MVP** |  |
| `delivery_policy.py` | **MVP** |  |

## interfaces/telegram/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **MVP** |  |
| `bot.py` | **MVP** |  |

## interfaces/webhooks/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **MVP** |  |
| `calendly.py` | **MVP** |  |
| `cc_receiver.py` | **MVP** |  |
| `higgsfield.py` | **FUTURE** |  |

## memory/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **MVP** |  |
| `embedder.py` | **MVP** |  |
| `storage.py` | **CORE** |  |
| `store.py` | **FUTURE** |  |

## objectives/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **FUTURE** |  |
| `arbitration.py` | **FUTURE** |  |

## persistence_layer/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **FUTURE** |  |
| `memory_fabric.py` | **FUTURE** |  |
| `persistence.py` | **FUTURE** |  |

## planning/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **FUTURE** |  |
| `directive_engine.py` | **FUTURE** |  |
| `hierarchical_planning.py` | **FUTURE** |  |
| `plan_mutation.py` | **FUTURE** |  |

## policy/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **FUTURE** |  |
| `foresight_engine.py` | **FUTURE** |  |
| `regime_engine.py` | **FUTURE** |  |
| `risk_model.py` | **FUTURE** |  |
| `stability_guard.py` | **FUTURE** |  |

## primitives/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **FUTURE** |  |
| `ontological.py` | **FUTURE** |  |

## protocols/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **FUTURE** |  |
| `adapters.py` | **FUTURE** |  |
| `capabilities.py` | **FUTURE** |  |
| `execution.py` | **FUTURE** |  |
| `governance.py` | **FUTURE** |  |
| `interpretation.py` | **FUTURE** |  |
| `memory.py` | **FUTURE** |  |
| `outcome.py` | **FUTURE** |  |
| `persistence.py` | **FUTURE** |  |
| `planning.py` | **FUTURE** |  |
| `security.py` | **FUTURE** |  |
| `signals.py` | **FUTURE** |  |
| `workstation.py` | **FUTURE** |  |
| `world.py` | **FUTURE** |  |

## reasoning/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **FUTURE** |  |
| `calibration.py` | **FUTURE** |  |
| `causal_attribution.py` | **FUTURE** |  |
| `causal_credit.py` | **FUTURE** |  |
| `causal_memory.py` | **FUTURE** |  |
| `context_engine.py` | **FUTURE** |  |
| `control_layer.py` | **FUTURE** |  |
| `convergence.py` | **FUTURE** |  |
| `counterfactual_eval.py` | **FUTURE** |  |
| `credit_assignment.py` | **FUTURE** |  |
| `influence_orchestrator.py` | **FUTURE** |  |
| `influence_scoring.py` | **FUTURE** |  |
| `meta_control.py` | **FUTURE** |  |
| `meta_generalization.py` | **FUTURE** |  |
| `meta_weight_engine.py` | **FUTURE** |  |
| `trap_recovery.py` | **FUTURE** |  |

## runtime_engine/

| File | Classification | Notes |
|---|---|---|
| `accountability.py` | **MVP** |  |
| `action_planner.py` | **FUTURE** |  |
| `action_schema.py` | **FUTURE** |  |
| `action_synthesis.py` | **DELETE_CANDIDATE** |  |
| `adaptive_exploration.py` | **FUTURE** |  |
| `adaptive_prompt.py` | **FUTURE** |  |
| `agent_hierarchy.py` | **CORE** |  |
| `agent_runtime.py` | **CORE** |  [REFACTOR_LATER] |
| `agent_teams.py` | **MVP** |  |
| `ai_identity.py` | **MVP** |  |
| `analytics_adapter.py` | **FUTURE** |  |
| `authority_engine.py` | **CORE** |  |
| `benchmark_env.py` | **FUTURE** |  |
| `calibration.py` | **FUTURE** |  |
| `causal_attribution.py` | **FUTURE** |  |
| `causal_credit.py` | **DELETE_CANDIDATE** |  |
| `causal_memory.py` | **FUTURE** |  |
| `cc_sdk.py` | **CORE** |  |
| `ceo_agent.py` | **MVP** |  |
| `ceo_intelligence.py` | **MVP** |  |
| `ceo_operational_standards.py` | **MVP** |  |
| `claude_skill_registry.py` | **MVP** |  |
| `cognitive_loop.py` | **DELETE_CANDIDATE** |  |
| `commit_pipeline.py` | **CORE** |  |
| `confidentiality.py` | **MVP** |  |
| `context_builder.py` | **CORE** |  |
| `context_compaction.py` | **MVP** |  |
| `context_engine.py` | **FUTURE** |  |
| `control_layer.py` | **FUTURE** |  |
| `convergence.py` | **FUTURE** |  |
| `coordination_engine.py` | **MVP** |  |
| `counterfactual_eval.py` | **FUTURE** |  |
| `credit_assignment.py` | **FUTURE** |  |
| `daily_sync.py` | **MVP** |  |
| `db.py` | **CORE** |  |
| `decision_log.py` | **MVP** |  |
| `decision_trace.py` | **FUTURE** |  |
| `delegation_tracker.py` | **MVP** |  |
| `directive_engine.py` | **FUTURE** |  |
| `directive_memory.py` | **FUTURE** |  |
| `discord_utils.py` | **MVP** |  |
| `domain_adapter.py` | **FUTURE** |  |
| `ea_operational_standards.py` | **MVP** |  |
| `email_gps.py` | **MVP** |  |
| `embedding_engine.py` | **MVP** |  |
| `environment_router.py` | **FUTURE** |  |
| `event_bus.py` | **CORE** |  |
| `evolution_engine.py` | **MVP** |  |
| `execution_adapters.py` | **FUTURE** |  |
| `execution_budget.py` | **FUTURE** |  |
| `execution_credit.py` | **FUTURE** |  |
| `execution_engine.py` | **MVP** |  |
| `execution_feedback.py` | **FUTURE** |  |
| `execution_router.py` | **FUTURE** |  |
| `execution_spine.py` | **CORE** |  |
| `exploration_engine.py` | **FUTURE** |  |
| `fabric_analytics.py` | **DELETE_CANDIDATE** |  |
| `feedback_loop.py` | **MVP** |  |
| `foresight_engine.py` | **FUTURE** |  |
| `founder_rate.py` | **MVP** |  |
| `gateway.py` | **CORE** |  [REFACTOR_LATER] |
| `goal_alignment.py` | **FUTURE** |  |
| `goal_arbitrator.py` | **FUTURE** |  |
| `goal_evaluator.py` | **FUTURE** |  |
| `goal_mode.py` | **FUTURE** |  |
| `goal_validator.py` | **FUTURE** |  |
| `gws_connector.py` | **MVP** |  |
| `hierarchical_planning.py` | **FUTURE** |  |
| `human_intelligence.py` | **MVP** |  |
| `influence_orchestrator.py` | **FUTURE** |  |
| `influence_scoring.py` | **FUTURE** |  |
| `input_intelligence.py` | **MVP** |  |
| `intent_compiler.py` | **FUTURE** |  |
| `intent_router.py` | **MVP** |  |
| `knowledge_domains.py` | **MVP** |  |
| `knowledge_graph.py` | **MVP** |  |
| `knowledge_integrator.py` | **MVP** |  |
| `long_horizon_benchmark.py` | **FUTURE** |  |
| `martell_patterns.py` | **MVP** |  |
| `memory.py` | **CORE** |  |
| `memory_fabric.py` | **FUTURE** |  |
| `meta_control.py` | **FUTURE** |  |
| `meta_generalization.py` | **FUTURE** |  |
| `meta_goal.py` | **FUTURE** |  |
| `meta_weight_engine.py` | **FUTURE** |  |
| `model_preferences.py` | **CORE** |  |
| `model_router.py` | **CORE** |  |
| `multi_strategy.py` | **FUTURE** |  |
| `multi_world_policy.py` | **FUTURE** |  |
| `notebooklm_sync.py` | **MVP** |  |
| `notion_publisher.py` | **MVP** |  |
| `objective_arbitration.py` | **FUTURE** |  |
| `objective_decision_adapter.py` | **FUTURE** |  |
| `objective_engine.py` | **FUTURE** |  |
| `objective_optimizer.py` | **FUTURE** |  |
| `onboarding_backfill.py` | **MVP** |  |
| `orchestrator.py` | **CORE** |  |
| `outcome_evaluator.py` | **FUTURE** |  |
| `outcome_feedback.py` | **DELETE_CANDIDATE** |  |
| `output_validator.py` | **MVP** |  |
| `pattern_engine.py` | **FUTURE** |  |
| `persistence.py` | **FUTURE** |  |
| `plan_mutation.py` | **DELETE_CANDIDATE** |  |
| `policy_engine.py` | **FUTURE** |  |
| `policy_state.py` | **FUTURE** |  |
| `portfolio_advisor.py` | **MVP** |  |
| `portfolio_advisor_standards.py` | **MVP** |  |
| `primitives.py` | **CORE** |  |
| `principle_engine.py` | **MVP** |  |
| `proactive_engine.py` | **MVP** |  |
| `quality_gate.py` | **MVP** |  |
| `reality_context.py` | **MVP** |  |
| `reality_engine.py` | **MVP** |  |
| `regime_engine.py` | **FUTURE** |  |
| `research_engine.py` | **MVP** |  |
| `risk_model.py` | **FUTURE** |  |
| `score_distribution.py` | **FUTURE** |  |
| `self_awareness.py` | **MVP** |  |
| `session_interface.py` | **FUTURE** |  |
| `session_runtime.py` | **FUTURE** |  |
| `session_state.py` | **MVP** |  |
| `session_store.py` | **MVP** |  |
| `signal_hierarchy.py` | **MVP** |  |
| `signal_ingestion.py` | **FUTURE** |  |
| `signal_orchestrator.py` | **FUTURE** |  |
| `signal_router.py` | **FUTURE** |  |
| `signal_sensitivity.py` | **FUTURE** |  |
| `skill_improvement.py` | **MVP** |  |
| `skill_registry.py` | **CORE** |  |
| `stability_guard.py` | **FUTURE** |  |
| `stage_manager.py` | **MVP** |  |
| `status.py` | **MVP** |  |
| `strategy_abstraction.py` | **FUTURE** |  |
| `strategy_engine.py` | **MVP** |  |
| `strategy_mutation.py` | **DELETE_CANDIDATE** |  |
| `strategy_pattern_memory.py` | **DELETE_CANDIDATE** |  |
| `system_graph.py` | **FUTURE** |  |
| `system_registry.py` | **FUTURE** |  |
| `system_selector.py` | **FUTURE** |  |
| `tenant.py` | **MVP** |  |
| `trap_recovery_engine.py` | **FUTURE** |  |
| `user_model.py` | **MVP** |  |
| `venture_knowledge.py` | **CORE** |  |
| `voice_engine.py` | **MVP** |  |
| `voice_interface.py` | **MVP** |  |
| `world_pulse.py` | **MVP** |  |

## runtime_loop/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **MVP** |  |
| `action_executor.py` | **FUTURE** |  |
| `context.py` | **FUTURE** |  |
| `continuity_store.py` | **FUTURE** |  |
| `input_router.py` | **MVP** |  |
| `lifecycle.py` | **FUTURE** |  |
| `lifecycle_behaviors.py` | **FUTURE** |  |
| `lifecycle_hooks.py` | **FUTURE** |  |
| `live_loop.py` | **MVP** |  |
| `output_dispatcher.py` | **MVP** |  |
| `session_registry.py` | **MVP** |  |
| `session_router.py` | **MVP** |  |
| `surface_registry.py` | **MVP** |  |

## security/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **FUTURE** |  |
| `access.py` | **FUTURE** |  |

## signal/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **MVP** |  |
| `event_bus.py` | **MVP** |  |
| `hierarchy.py` | **FUTURE** |  |
| `ingest.py` | **MVP** |  |
| `router.py` | **FUTURE** |  |
| `sensitivity.py` | **FUTURE** |  |
| `types.py` | **CORE** |  |

## stages/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **CORE** |  |
| `authority.py` | **CORE** |  |
| `commit.py` | **CORE** |  |
| `context_assembly.py` | **CORE** |  |
| `enhancement.py` | **CORE** |  |
| `footer.py` | **MVP** |  |
| `llm_generation.py` | **CORE** |  |
| `outcome.py` | **MVP** |  |
| `quality.py` | **MVP** |  |
| `stage_filter.py` | **MVP** |  |

## storage/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **CORE** |  |
| `backend.py` | **CORE** |  |

## storage/adapters/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **CORE** |  |
| `neon.py` | **CORE** |  |

## strategy/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **FUTURE** |  |
| `interfaces.py` | **FUTURE** |  |
| `memory.py` | **FUTURE** |  |

## substrate/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **CORE** |  [REFACTOR_LATER] |
| `action_tracker.py` | **FUTURE** |  |
| `actions.py` | **MVP** |  |
| `app_allowlist.py` | **FUTURE** |  |
| `artifact_contract.py` | **MVP** |  |
| `audio_loop.py` | **FUTURE** |  |
| `auto_task_generation.py` | **FUTURE** |  |
| `autonomy_policy.py` | **MVP** |  |
| `browser_agent.py` | **FUTURE** |  |
| `browser_policy.py` | **FUTURE** |  |
| `capabilities.py` | **FUTURE** |  |
| `capability_routing.py` | **FUTURE** |  |
| `capability_tagging.py` | **MVP** |  |
| `checkpoint_runtime.py` | **CORE** |  |
| `claude_responder.py` | **MVP** |  |
| `claude_session_bridge.py` | **MVP** |  |
| `composition_engine.py` | **FUTURE** |  |
| `context_lifecycle.py` | **FUTURE** |  |
| `continuity_summary.py` | **FUTURE** |  |
| `control_commands.py` | **FUTURE** |  |
| `conversation_router.py` | **FUTURE** |  |
| `daily_rituals.py` | **MVP** |  |
| `day_workflows.py` | **MVP** |  |
| `decision_engine.py` | **MVP** |  |
| `decision_events.py` | **MVP** |  |
| `discord_ingress_adapter.py` | **FUTURE** |  |
| `discord_mode_routing.py` | **MVP** |  |
| `discord_output_policy.py` | **MVP** |  |
| `discord_text_transport.py` | **MVP** |  |
| `discord_voice_playback.py` | **FUTURE** |  |
| `discord_voice_transport.py` | **FUTURE** |  |
| `dispatch_enforcement.py` | **FUTURE** |  |
| `event_log_runtime.py` | **CORE** |  |
| `event_scheduler.py` | **CORE** |  |
| `event_spine.py` | **MVP** |  |
| `event_store.py` | **MVP** |  |
| `execution_adapter.py` | **MVP** |  |
| `execution_authority.py` | **MVP** |  |
| `execution_batch.py` | **MVP** |  |
| `execution_bootstrap.py` | **MVP** |  |
| `execution_constraints.py` | **FUTURE** |  |
| `execution_contract.py` | **CORE** |  |
| `execution_control.py` | **FUTURE** |  |
| `execution_events.py` | **MVP** |  |
| `execution_result_handler.py` | **MVP** |  |
| `execution_router.py` | **MVP** |  |
| `execution_scope.py` | **FUTURE** |  |
| `execution_trace.py` | **MVP** |  |
| `execution_worker.py` | **MVP** |  |
| `google_meet_source.py` | **FUTURE** |  |
| `handoff_artifact.py` | **FUTURE** |  |
| `intent_coordinator.py` | **MVP** |  |
| `intent_memory.py` | **MVP** |  |
| `intent_models.py` | **MVP** |  |
| `interaction_archive.py` | **MVP** |  |
| `lifecycle_handlers.py` | **MVP** |  |
| `live_session.py` | **FUTURE** |  |
| `live_session_controller.py` | **FUTURE** |  |
| `live_sessions.py` | **FUTURE** |  |
| `live_turn.py` | **FUTURE** |  |
| `llm_decision_events.py` | **FUTURE** |  |
| `llm_outcomes.py` | **FUTURE** |  |
| `llm_planner.py` | **FUTURE** |  |
| `llm_replay.py` | **FUTURE** |  |
| `local_control.py` | **FUTURE** |  |
| `local_listener.py` | **FUTURE** |  |
| `meet_caption_bridge.py` | **FUTURE** |  |
| `meeting_intelligence.py` | **FUTURE** |  |
| `meeting_sources.py` | **FUTURE** |  |
| `meeting_transport.py` | **FUTURE** |  |
| `message_framing.py` | **MVP** |  |
| `mode_behavior.py` | **MVP** |  |
| `node_controller.py` | **FUTURE** |  |
| `node_transport.py` | **FUTURE** |  |
| `nodes.py` | **MVP** |  |
| `operator_approvals.py` | **FUTURE** |  |
| `operator_artifacts.py` | **MVP** |  |
| `operator_delivery.py` | **MVP** |  |
| `operator_presence.py` | **FUTURE** |  |
| `operator_session.py` | **MVP** |  |
| `operator_state.py` | **FUTURE** |  |
| `operator_trace.py` | **MVP** |  |
| `operator_transitions.py` | **FUTURE** |  |
| `orchestration_bootstrap.py` | **MVP** |  |
| `orchestration_mode.py` | **MVP** |  |
| `os_controller.py` | **FUTURE** |  |
| `perception.py` | **FUTURE** |  |
| `pipeline.py` | **FUTURE** |  |
| `pipeline_execution.py` | **FUTURE** |  |
| `plan_executor.py` | **FUTURE** |  |
| `plan_mutation.py` | **MVP** |  |
| `plan_registry.py` | **MVP** |  |
| `plan_scoring.py` | **MVP** |  |
| `planner.py` | **MVP** |  |
| `planner_events.py` | **MVP** |  |
| `playback_status.py` | **FUTURE** |  |
| `presence_runtime.py` | **FUTURE** |  |
| `presence_state.py` | **FUTURE** |  |
| `profile_resolution.py` | **FUTURE** |  |
| `ptt_binding.py` | **FUTURE** |  |
| `query_brain.py` | **FUTURE** |  |
| `remote_executor.py` | **FUTURE** |  |
| `replay_validation.py` | **FUTURE** |  |
| `resource_guard.py` | **FUTURE** |  |
| `result_query.py` | **FUTURE** |  |
| `result_store.py` | **MVP** |  |
| `ritual_body.py` | **MVP** |  |
| `ritual_execution_driver.py` | **MVP** |  |
| `ritual_inference.py` | **FUTURE** |  |
| `ritual_reconciler.py` | **FUTURE** |  |
| `ritual_runner.py` | **MVP** |  |
| `rituals.py` | **MVP** |  |
| `role_resolver.py` | **FUTURE** |  |
| `roles.py` | **FUTURE** |  |
| `run_execution.py` | **MVP** |  |
| `run_lifecycle.py` | **MVP** |  |
| `runtime_bootstrap.py` | **CORE** |  |
| `runtime_continuity.py` | **FUTURE** |  |
| `runtime_mode.py` | **FUTURE** |  |
| `runtime_profile.py` | **FUTURE** |  |
| `runtime_rehydration.py` | **CORE** |  |
| `runtime_session.py` | **FUTURE** |  |
| `runtime_state_store.py` | **CORE** |  |
| `scene_capabilities.py` | **FUTURE** |  |
| `scene_policy.py` | **FUTURE** |  |
| `scenes.py` | **FUTURE** |  |
| `score_meta.py` | **MVP** |  |
| `session_control.py` | **MVP** |  |
| `session_discord_bridge.py` | **MVP** |  |
| `session_orchestration.py` | **FUTURE** |  |
| `session_watcher.py` | **MVP** |  |
| `spec_validation.py` | **FUTURE** |  |
| `station.py` | **MVP** |  |
| `station_bus.py` | **MVP** |  |
| `station_daemon.py` | **MVP** |  |
| `station_drainer.py` | **MVP** |  |
| `station_helpers.py` | **MVP** |  |
| `station_presence.py` | **MVP** |  |
| `station_readiness.py` | **FUTURE** |  |
| `station_triggers.py` | **FUTURE** |  |
| `storage.py` | **CORE** |  |
| `stream_transport_contract.py` | **FUTURE** |  |
| `stt_producer.py` | **FUTURE** |  |
| `target_policy.py` | **MVP** |  |
| `task_checkpoint.py` | **FUTURE** |  |
| `task_decomposition.py` | **MVP** |  |
| `task_execution.py` | **MVP** |  |
| `task_pipeline.py` | **MVP** |  |
| `task_queue.py` | **FUTURE** |  |
| `task_record.py` | **FUTURE** |  |
| `task_system.py` | **MVP** |  |
| `transcript_inject.py` | **FUTURE** |  |
| `transport_report.py` | **FUTURE** |  |
| `trigger_adapters.py` | **MVP** |  |
| `tts_sanitize.py` | **MVP** |  |
| `voice_eos_responder.py` | **FUTURE** |  |
| `voice_session.py` | **FUTURE** |  |
| `voice_transport_contract.py` | **FUTURE** |  |
| `voice_wake.py` | **FUTURE** |  |
| `wake_producer.py` | **FUTURE** |  |
| `workflow_delegation.py` | **FUTURE** |  |
| `workflow_driver.py` | **MVP** |  |
| `workflow_execution.py` | **FUTURE** |  |
| `workload_policy.py` | **FUTURE** |  |
| `workstation_log.py` | **FUTURE** |  |
| `workstation_profile_contract.py` | **FUTURE** |  |
| `workstation_runtime.py` | **FUTURE** |  |

## workstation/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **MVP** |  |
| `business.py` | **MVP** |  |
| `profile.py` | **FUTURE** |  |

## world/

| File | Classification | Notes |
|---|---|---|
| `__init__.py` | **MVP** |  |
| `calibration.py` | **FUTURE** |  |
| `dynamics_adapter.py` | **FUTURE** |  |
| `model.py` | **CORE** |  |
| `reasoning.py` | **FUTURE** |  |
| `simulation.py` | **FUTURE** |  |
| `state.py` | **FUTURE** |  |
| `substrate.py` | **MVP** |  |
| `types.py` | **FUTURE** |  |
