# Future Trajectory Preservation Audit

**Date:** 2026-04-26
**Scope:** All files under `/opt/OS/umh/` analyzed for strategic future value
**Method:** Static import tracing from 5 production entry points (discord bot, telegram bot, orchestrator, dm_monitor, webhooks), line counting, duplicate detection, test coverage mapping

## Codebase Vital Signs

| Metric | Count |
|---|---|
| Total Python files (non-init) | 489 |
| Total lines of Python | 197,401 |
| Production-reachable files | 316 |
| Unreachable from production | 173 |
| Unreachable lines | 65,255 |
| Duplicate file pairs (runtime_engine vs modular) | 37 |
| Identical duplicates | 17 |
| Diverged duplicates | 20 |

---

## Duplicate File Warning

A significant structural issue: 37 files exist in both `runtime_engine/` (the legacy monolith directory) and newer modular directories (`reasoning/`, `analytics/`, `goals/`, `planning/`, `policy/`, `feedback/`, `world/`, `persistence_layer/`, `signal/`, `strategy/`). Of these, 17 are byte-identical copies and 20 have diverged. Production import paths currently reference BOTH locations depending on the caller. This creates a real risk of one copy being updated while the other stagnates.

**Identical pairs** (safe to deduplicate -- keep the modular version):
- `reasoning/causal_memory.py`, `reasoning/context_engine.py`, `reasoning/credit_assignment.py`, `reasoning/influence_scoring.py`, `reasoning/meta_control.py`, `reasoning/meta_generalization.py`
- `analytics/score_distribution.py`, `analytics/signal_orchestrator.py`, `analytics/strategy_pattern_memory.py`
- `planning/directive_engine.py`
- `policy/foresight_engine.py`, `policy/regime_engine.py`, `policy/risk_model.py`, `policy/stability_guard.py`
- `persistence_layer/persistence.py`

**Diverged pairs** (require manual reconciliation before dedup):
- `reasoning/calibration.py`, `reasoning/causal_attribution.py`, `reasoning/causal_credit.py`, `reasoning/control_layer.py`, `reasoning/convergence.py`, `reasoning/counterfactual_eval.py`, `reasoning/influence_orchestrator.py`, `reasoning/meta_weight_engine.py`
- `analytics/adaptive_exploration.py`, `analytics/exploration_engine.py`, `analytics/fabric_analytics.py`, `analytics/pattern_engine.py`, `analytics/strategy_mutation.py`
- `goals/meta_goal.py`
- `planning/hierarchical_planning.py`, `planning/plan_mutation.py`
- `feedback/outcome_evaluator.py`, `feedback/outcome_feedback.py`
- `persistence_layer/memory_fabric.py`
- `signal/event_bus.py` (225 vs 424 lines)
- `strategy/memory.py` (395 vs 1024 lines)

---

## Area 1: Memory / Knowledge / World Model

**Files (36 total, 12,501 lines):**

| File | Lines | Reachable | Importers |
|---|---|---|---|
| `runtime_engine/knowledge_domains.py` | 1,143 | Yes | -- |
| `runtime_engine/memory.py` | 1,024 | Yes | 9 |
| `world/simulation.py` | 968 | Yes | 2 |
| `world/state.py` | 928 | Yes | -- |
| `persistence_layer/persistence.py` | 754 | Yes | -- |
| `substrate/query_brain.py` | 749 | Yes | -- |
| `world/reasoning.py` | 622 | Yes | 2 |
| `world/calibration.py` | 565 | Yes | -- |
| `runtime_engine/knowledge_graph.py` | 529 | Yes | -- |
| `runtime_engine/memory_fabric.py` | 428 | No | 0 |
| `persistence_layer/memory_fabric.py` | 428 | Yes | -- |
| `runtime_engine/embedding_engine.py` | 415 | Yes | 2 |
| `strategy/memory.py` | 395 | Yes | -- |
| `reasoning/causal_memory.py` | 388 | Yes | -- |
| `world/substrate.py` | 379 | Yes | -- |
| `runtime_engine/venture_knowledge.py` | 376 | Yes | 5 |
| `reasoning/context_engine.py` | 370 | Yes | -- |
| `world/model.py` | 350 | Yes | -- |
| `substrate/intent_memory.py` | 349 | No | 0 |
| `runtime_engine/directive_memory.py` | 256 | Yes | -- |
| `runtime_engine/knowledge_integrator.py` | 240 | Yes | 2 |
| `world/dynamics_adapter.py` | 228 | Yes | 2 |
| `world/types.py` | 165 | Yes | 4 |
| `storage/adapters/neon.py` | 147 | Yes | 9 |
| `memory/store.py` | 70 | No | 0 |
| `memory/embedder.py` | 69 | Yes | -- |
| `memory/storage.py` | 54 | Yes | -- |
| `storage/backend.py` | 36 | Yes | 2 |
| `protocols/memory.py` | 31 | No | 0 |
| `protocols/world.py` | 21 | No | 0 |
| `protocols/persistence.py` | 8 | Yes | -- |

**Current State:** Partially used. The `world/` subsystem is fully production-reachable (8 files, well-tested with 8 test files). Memory and knowledge graph are actively used. `memory_fabric.py` in runtime_engine is an orphaned duplicate. Protocol files are interface stubs.

**Why It Matters:** The world model is the foundation of EOS's ability to reason about the founder's business reality. Knowledge domains and graphs give the system institutional memory that survives sessions. Without these, EOS is a stateless chatbot.

**Phase:** Phase 1 (world model active now) through Phase 4 (knowledge graph becomes multi-tenant)

**Recommendation:** Preserve all. Deduplicate `memory_fabric.py`. Delete orphaned `memory/store.py` and protocol stubs only after confirming no planned use.

**Risk of Deletion:** CATASTROPHIC for world/ and memory.py; HIGH for knowledge_graph/knowledge_domains; MEDIUM for protocol stubs

---

## Area 2: Workstation / Jarvis / Voice

**Files (44 total, ~16,500 lines):**

| File | Lines | Reachable | Notes |
|---|---|---|---|
| `substrate/claude_session_bridge.py` | 1,160 | Yes | Claude Code integration |
| `substrate/stt_producer.py` | 1,146 | No | Speech-to-text pipeline |
| `substrate/local_control.py` | 945 | Yes | Local machine control |
| `substrate/station_daemon.py` | 859 | Yes | Always-on station process |
| `runtime_engine/voice_interface.py` | 825 | Yes | Voice pipeline abstraction |
| `substrate/discord_voice_transport.py` | 804 | Yes | Voice I/O over Discord |
| `substrate/voice_session.py` | 789 | Yes | Voice session management |
| `adapters/voice_loop.py` | 721 | No | Continuous voice loop |
| `substrate/os_controller.py` | 712 | No | OS-level mouse/keyboard/window |
| `substrate/discord_voice_playback.py` | 650 | Yes | TTS playback to Discord |
| `runtime_engine/voice_engine.py` | 630 | Yes | Voice routing engine |
| `substrate/audio_loop.py` | 612 | Yes | Audio capture/playback |
| `substrate/browser_agent.py` | 527 | Yes | Browser automation |
| `substrate/wake_producer.py` | 490 | Yes | Wake word detection |
| `workstation/business.py` | 478 | Yes | Business context for AI |
| `substrate/local_listener.py` | 396 | Yes | Local event listener |
| `substrate/workstation_runtime.py` | 387 | No | Workstation daemon |
| `substrate/station_triggers.py` | 381 | No | Event triggers for station |
| `substrate/ptt_binding.py` | 381 | No | Push-to-talk key binding |
| `substrate/workstation_profile_contract.py` | 380 | No | Profile spec for workstation |
| `substrate/voice_wake.py` | 380 | No | Wake word engine |
| `adapters/voice_state.py` | 367 | No | Voice state machine |
| `substrate/station_drainer.py` | 347 | No | Queue drainer for station |
| `substrate/voice_eos_responder.py` | 338 | Yes | Voice response generation |
| `substrate/station_presence.py` | 334 | Yes | Presence detection |
| `substrate/station_readiness.py` | 305 | Yes | Readiness checks |
| `substrate/stream_transport_contract.py` | 284 | No | Stream protocol spec |
| `substrate/voice_transport_contract.py` | 270 | No | Voice transport spec |
| `substrate/browser_policy.py` | 245 | Yes | Browser safety rules |
| `substrate/workstation_log.py` | 233 | Yes | Workstation event log |
| `substrate/station.py` | 227 | Yes | Station event types |
| `adapters/tts_engine.py` | 202 | No | TTS adapter interface |
| `adapters/stt_engine.py` | 193 | No | STT adapter interface |
| `adapters/workstation_adapter.py` | 189 | No | Workstation adapter |
| `substrate/station_bus.py` | 187 | Yes | Station event bus |
| `substrate/tts_sanitize.py` | 180 | Yes | TTS text cleanup |
| `substrate/claude_responder.py` | 178 | Yes | Claude response formatting |
| `substrate/station_helpers.py` | 127 | Yes | Station utilities |
| `adapters/voice_adapter.py` | 124 | No | Voice adapter interface |
| `workstation/profile.py` | 94 | No | Workstation profile |
| `substrate/playback_status.py` | 92 | Yes | Audio playback tracking |
| `substrate/app_allowlist.py` | 70 | Yes | App security allowlist |
| `adapters/execution/workstation_adapter.py` | 189 | No | Execution workstation bridge |

**Current State:** Partially used. Voice pipeline is production-reachable through Discord voice. Station/workstation subsystem has 12 files reachable + 13 unreachable. The full Jarvis local experience (os_controller, ptt_binding, voice_wake, stt_producer) exists as complete implementations but is not wired into any production service.

**Why It Matters:** This IS the Jarvis vision. 16,500 lines of voice/local/workstation code represent the transition from "Discord bot" to "always-on AI presence." The stt_producer alone is 1,146 lines of real speech-to-text pipeline code.

**Phase:** Phase 2 (post-$10K, workstation daemon) through Phase 3 (multi-device, full Jarvis)

**Recommendation:** Preserve all. These are the single largest investment in the Jarvis trajectory. Station and voice files have existing tests.

**Risk of Deletion:** CATASTROPHIC -- this is months of specialized infrastructure that cannot be rebuilt quickly

---

## Area 3: Cross-Device / Sessions / Continuity

**Files (37 total, ~14,500 lines):**

| File | Lines | Reachable | Notes |
|---|---|---|---|
| `runtime_engine/session_runtime.py` | 3,685 | Yes | Core session management (largest file in UMH) |
| `runtime_engine/session_interface.py` | 805 | No | Session API surface |
| `substrate/session_watcher.py` | 748 | Yes | Session lifecycle monitor |
| `substrate/continuity_summary.py` | 670 | No | Session handoff summaries |
| `substrate/live_sessions.py` | 634 | Yes | Active session registry |
| `substrate/live_session_controller.py` | 577 | No | Session orchestration |
| `substrate/handoff_artifact.py` | 456 | Yes | Cross-device handoff data |
| `substrate/session_discord_bridge.py` | 442 | Yes | Discord session adapter |
| `substrate/session_orchestration.py` | 417 | No | Multi-session coordination |
| `substrate/live_session.py` | 416 | No | Single session model |
| `runtime_loop/session_registry.py` | 414 | Yes | Session discovery |
| `substrate/node_controller.py` | 356 | Yes | Multi-node dispatch |
| `substrate/live_turn.py` | 340 | No | Conversational turn tracking |
| `runtime_loop/lifecycle.py` | 339 | Yes | Runtime lifecycle |
| `runtime_loop/live_loop.py` | 306 | Yes | Main runtime loop |
| `substrate/runtime_continuity.py` | 302 | No | Runtime state persistence |
| `substrate/node_transport.py` | 290 | Yes | Inter-node communication |
| `substrate/runtime_session.py` | 264 | No | Runtime-level session |
| `substrate/runtime_profile.py` | 264 | Yes | Runtime config profile |
| `substrate/session_control.py` | 259 | Yes | Session control commands |
| `substrate/capability_routing.py` | 230 | Yes | Route by device capability |
| `substrate/runtime_state_store.py` | 218 | Yes | Persistent runtime state |
| `runtime_loop/action_executor.py` | 206 | Yes | Action execution |
| `substrate/checkpoint_runtime.py` | 200 | Yes | Checkpoint/restore |
| `runtime_loop/output_dispatcher.py` | 186 | No | Multi-surface output |
| `runtime_loop/surface_registry.py` | 173 | Yes | I/O surface registry |
| `substrate/runtime_rehydration.py` | 162 | Yes | State rehydration |
| `runtime_engine/environment_router.py` | 162 | No | Environment-based routing |
| `runtime_loop/lifecycle_behaviors.py` | 153 | Yes | Lifecycle event handlers |
| `runtime_loop/input_router.py` | 127 | Yes | Input routing |
| `runtime_loop/session_router.py` | 98 | Yes | Session routing |
| `runtime_loop/lifecycle_hooks.py` | 92 | Yes | Lifecycle hook system |
| `runtime_engine/session_state.py` | 90 | Yes | Session state (used by Claude Code) |
| `runtime_engine/session_store.py` | 55 | Yes | Session persistence |
| `runtime_loop/continuity_store.py` | 49 | Yes | Continuity persistence |
| `runtime_loop/context.py` | 43 | Yes | Runtime context |

**Current State:** Partially used. `session_runtime.py` (3,685 lines) is the largest file in UMH and is production-active. Node controller and transport are reachable. Continuity summary, session orchestration, and live_session_controller are built but not yet wired in. 12 test files cover continuity.

**Why It Matters:** Cross-device continuity is what makes EOS a persistent presence rather than isolated chat sessions. The handoff artifact, continuity summary, and node transport represent the ability to start a task on your phone and finish it on your laptop.

**Phase:** Phase 2 (session persistence) through Phase 3 (multi-node orchestration)

**Recommendation:** Preserve all. `session_runtime.py` is the nervous system of the entire platform.

**Risk of Deletion:** CATASTROPHIC for session_runtime; HIGH for continuity/handoff files

---

## Area 4: Perception / Auto-Task

**Files (17 total, ~5,700 lines):**

| File | Lines | Reachable | Notes |
|---|---|---|---|
| `substrate/perception.py` | 993 | Yes | Ambient sensing layer |
| `substrate/local_control.py` | 945 | Yes | Local system commands |
| `runtime_engine/signal_orchestrator.py` | 607 | No (dupe) | Signal routing |
| `runtime_engine/proactive_engine.py` | 431 | Yes | Proactive task generation |
| `substrate/local_listener.py` | 396 | Yes | Local event listener |
| `substrate/auto_task_generation.py` | 290 | Yes | Auto task from perception |
| `signal/sensitivity.py` | 276 | No (dupe) | Signal sensitivity |
| `runtime_engine/signal_sensitivity.py` | 276 | Yes | Signal sensitivity (active) |
| `signal/hierarchy.py` | 249 | No (dupe) | Signal priority |
| `runtime_engine/signal_hierarchy.py` | 249 | Yes | Signal priority (active) |
| `signal/event_bus.py` | 225 | Yes | Event distribution |
| `runtime_engine/signal_ingestion.py` | 215 | Yes | Signal intake |
| `signal/router.py` | 177 | Yes | Signal routing |
| `runtime_engine/signal_router.py` | 177 | Yes | Signal routing (dupe) |
| `signal/ingest.py` | 120 | Yes | Signal ingestion |
| `signal/types.py` | 74 | Yes | Signal type definitions |

**Current State:** Partially used. Perception and auto_task_generation are reachable from production. The proactive engine is active. Signal subsystem has both modular and runtime_engine copies. 1 test file for perception.

**Why It Matters:** Perception is the bridge from "reactive assistant" to "proactive agent." Auto-task generation + perception means EOS notices things before you ask. This is table stakes for any autonomous system.

**Phase:** Phase 2 (enhanced perception) through Phase 3 (full ambient awareness)

**Recommendation:** Preserve all. Deduplicate signal files.

**Risk of Deletion:** HIGH -- perception layer is foundational for autonomy trajectory

---

## Area 5: Meeting Intelligence

**Files (6 total, 4,464 lines):**

| File | Lines | Reachable | Notes |
|---|---|---|---|
| `substrate/meeting_intelligence.py` | 2,180 | No | Full meeting AI (summary, intervention, memory extraction) |
| `substrate/meeting_transport.py` | 1,011 | No | Audio/caption transport |
| `substrate/meet_caption_bridge.py` | 542 | No | Google Meet caption ingestion |
| `substrate/google_meet_source.py` | 354 | No | Meet API source |
| `substrate/transcript_inject.py` | 204 | Yes | Transcript injection |
| `substrate/meeting_sources.py` | 173 | No | Meeting source registry |

**Current State:** Not used in production. Zero importers from production code path for meeting_intelligence (only imported by meeting_transport and transport_report, neither of which are production-reachable). Transcript inject is reachable. No test files for meeting area.

**Why It Matters:** Meeting intelligence is a complete, 4,464-line implementation of real-time meeting AI -- rolling summaries, intervention engine with cooldown, decision extraction, memory generation. This is a differentiating capability for the Empyrean Studio AI service offer and personal productivity.

**Phase:** Phase 2 (Empyrean Studio AI offer requires meeting intelligence)

**Recommendation:** Preserve. Needs tests before activation. This is the most complete unreachable subsystem in the codebase.

**Risk of Deletion:** CATASTROPHIC -- 4,464 lines of specialized meeting AI that took significant effort to build. Represents a direct revenue capability.

---

## Area 6: Goal-Directed Autonomy

**Files (64 total, ~26,000 lines):**

| File | Lines | Reachable | Notes |
|---|---|---|---|
| `substrate/plan_executor.py` | 1,332 | No | Multi-mode plan execution |
| `runtime_engine/hierarchical_planning.py` | 1,213 | No (dupe) | Hierarchical planner |
| `planning/hierarchical_planning.py` | 1,213 | Yes | Hierarchical planner (active) |
| `goals/meta_goal.py` | 841 | Yes | Meta-goal framework |
| `runtime_engine/meta_goal.py` | 841 | No (dupe) | -- |
| `runtime_engine/multi_strategy.py` | 785 | Yes | Multi-strategy evaluation |
| `planning/plan_mutation.py` | 764 | Yes | Plan adaptation |
| `substrate/llm_planner.py` | 751 | No | LLM-backed planning |
| `runtime_engine/reality_engine.py` | 631 | Yes | Reality grounding |
| `substrate/task_system.py` | 601 | Yes | Task management |
| `goals/engine.py` | 542 | No | Goal engine core |
| `substrate/task_execution.py` | 503 | Yes | Task execution |
| `planning/directive_engine.py` | 493 | Yes | Directive execution |
| `substrate/task_record.py` | 490 | Yes | Task history |
| `substrate/plan_scoring.py` | 483 | No | Plan quality scoring |
| `substrate/task_pipeline.py` | 480 | Yes | Task pipeline |
| `goals/state.py` | 472 | Yes | Goal state tracking |
| `substrate/plan_mutation.py` | 463 | No | Plan adaptation (substrate) |
| `substrate/planner.py` | 461 | No | Planning orchestrator |
| `goals/validator.py` | 458 | Yes | Goal validation |
| `policy/risk_model.py` | 456 | No (dupe) | Risk assessment |
| `goals/credit.py` | 454 | No | Goal credit assignment |
| `substrate/plan_registry.py` | 453 | No | Plan storage |
| `goals/alignment.py` | 428 | Yes | Goal alignment checking |
| `runtime_engine/policy_state.py` | 416 | Yes | Policy state |
| `goals/objective.py` | 416 | No | Objective decomposition |
| `runtime_engine/multi_world_policy.py` | 413 | Yes | Multi-scenario policy |
| `substrate/task_checkpoint.py` | 380 | No | Task checkpoint/resume |
| `policy/foresight_engine.py` | 379 | No (dupe) | Foresight planning |
| `objectives/arbitration.py` | 375 | No | Objective conflict resolution |
| `policy/regime_engine.py` | 363 | No (dupe) | Policy regime management |
| `substrate/decision_engine.py` | 320 | No | Decision making |
| `goals/arbitrator.py` | 314 | No | Goal conflict resolution |
| `runtime_engine/policy_engine.py` | 305 | Yes | Policy enforcement |
| `substrate/decision_events.py` | 255 | No | Decision event logging |
| `substrate/task_queue.py` | 244 | Yes | Task queue |
| `substrate/llm_outcomes.py` | 235 | No | LLM outcome tracking |
| `substrate/task_decomposition.py` | 224 | Yes | Task breakdown |
| `goals/budget.py` | 221 | No | Goal resource budgeting |
| `runtime_engine/objective_engine.py` | 212 | Yes | Objective management |
| `goals/evaluator.py` | 207 | No | Goal evaluation |
| `substrate/llm_decision_events.py` | 205 | No | LLM decision events |
| `runtime_engine/objective_optimizer.py` | 196 | Yes | Objective optimization |
| `goals/mode.py` | 193 | Yes | Goal mode selection |
| `substrate/planner_events.py` | 131 | No | Planner event logging |
| `substrate/autonomy_policy.py` | 111 | No | Autonomy guardrails |
| `policy/stability_guard.py` | 108 | No (dupe) | Stability protection |
| `goals/interfaces.py` | 70 | Yes | Goal interfaces |
| `protocols/planning.py` | 16 | No | Planning protocol |

**Current State:** Partially used. Goal state, validator, alignment, mode are all production-reachable (8 tests for goals). The planning layer (hierarchical_planning, plan_mutation, directive_engine) is reachable through runtime_engine imports. The substrate planning layer (planner, plan_executor, plan_scoring, plan_registry) is NOT reachable -- these are the next-gen planning implementations. 26 test files cover goals.

**Why It Matters:** Goal-directed autonomy is the single defining feature that separates EOS from every other AI wrapper. The substrate planning layer (plan_executor with multi-mode execution, llm_planner with LLM-backed planning, plan_scoring) represents the next evolution where the system doesn't just respond to commands but pursues objectives.

**Phase:** Phase 1 (basic goals active now) through Phase 4 (full autonomous goal pursuit)

**Recommendation:** Preserve all. Deduplicate runtime_engine copies. The substrate planning layer needs tests before activation.

**Risk of Deletion:** CATASTROPHIC for goals/ and planning/; HIGH for substrate planning files

---

## Area 7: Self-Improvement / Meta-Learning

**Files (46 total, ~19,000 lines):**

| File | Lines | Reachable | Notes |
|---|---|---|---|
| `runtime_engine/benchmark_env.py` | 1,636 | No | Decision quality benchmarking |
| `runtime_engine/evolution_engine.py` | 903 | Yes | System self-evolution |
| `runtime_engine/long_horizon_benchmark.py` | 832 | No | Long-term benchmark suite |
| `runtime_engine/self_awareness.py` | 698 | Yes | System self-model |
| `reasoning/meta_generalization.py` | 690 | Yes | Cross-domain learning |
| `reasoning/counterfactual_eval.py` | 630 | Yes | What-if analysis |
| `analytics/signal_orchestrator.py` | 607 | Yes | Signal analytics |
| `runtime_engine/strategy_engine.py` | 594 | Yes | Strategy management |
| `analytics/strategy_mutation.py` | 536 | Yes | Strategy adaptation |
| `reasoning/causal_credit.py` | 517 | Yes | Causal credit assignment |
| `analytics/fabric_analytics.py` | 489 | Yes | Fabric-level analytics |
| `runtime_engine/skill_improvement.py` | 448 | Yes | Skill auto-improvement |
| `runtime_engine/strategy_abstraction.py` | 447 | No | Strategy abstraction |
| `analytics/strategy_synthesizer.py` | 431 | Yes | Strategy synthesis |
| `analytics/strategy_pattern_memory.py` | 401 | Yes | Pattern memory |
| `analytics/pattern_engine.py` | 397 | Yes | Pattern detection |
| `reasoning/convergence.py` | 396 | Yes | Convergence detection |
| `reasoning/credit_assignment.py` | 391 | Yes | Credit assignment |
| `reasoning/causal_memory.py` | 388 | Yes | Causal memory |
| `reasoning/context_engine.py` | 370 | Yes | Context reasoning |
| `reasoning/calibration.py` | 344 | Yes | Reasoning calibration |
| `reasoning/meta_control.py` | 343 | Yes | Meta-cognitive control |
| `reasoning/influence_orchestrator.py` | 312 | Yes | Influence tracking |
| `analytics/exploration_engine.py` | 310 | Yes | Exploration vs exploitation |
| `reasoning/meta_weight_engine.py` | 304 | Yes | Weight tuning |
| `reasoning/influence_scoring.py` | 284 | Yes | Influence measurement |
| `feedback/outcome_evaluator.py` | 275 | Yes | Outcome evaluation |
| `analytics/adaptive_exploration.py` | 258 | Yes | Adaptive exploration |
| `feedback/outcome_feedback.py` | 251 | Yes | Feedback loop |
| `feedback/dynamics.py` | 233 | No | Feedback dynamics |
| `reasoning/control_layer.py` | 213 | Yes | Control layer |
| `reasoning/causal_attribution.py` | 196 | Yes | Causal attribution |
| `reasoning/trap_recovery.py` | 195 | No | Trap detection/recovery |
| `runtime_engine/trap_recovery_engine.py` | 195 | Yes | Trap recovery (active) |
| `analytics/score_distribution.py` | 190 | Yes | Score analysis |
| `feedback/loop.py` | 115 | Yes | Core feedback loop |

Plus ~10 duplicate copies in runtime_engine/ (see duplicate table above).

**Current State:** Mostly reachable. The reasoning and analytics subsystems are heavily imported. Benchmark environment (2,468 lines total across 2 files) is unreachable -- it's an offline evaluation system. Evolution engine, self-awareness, skill improvement are all production-active. 2 test files for benchmarks, tests for meta_generalization, meta_control, pattern_engine.

**Why It Matters:** This is EOS's ability to learn from its own performance. Without strategy mutation, causal credit, and counterfactual evaluation, the system cannot improve over time. The benchmark environment validates that improvements are real. This is the entire "intelligence" in artificial intelligence.

**Phase:** Phase 1 (reasoning active now) through Phase 4 (fully autonomous self-improvement)

**Recommendation:** Preserve all. Benchmark files should be promoted to regular test infrastructure. Deduplicate runtime_engine copies.

**Risk of Deletion:** CATASTROPHIC for reasoning/ and analytics/; HIGH for benchmark files

---

## Area 8: Execution Infrastructure

**Files (72 total, ~23,000 lines):**

| File | Lines | Reachable | Notes |
|---|---|---|---|
| `runtime_engine/gateway.py` | 1,839 | Yes | Main gateway (CONFIRMED WORKING) |
| `substrate/run_lifecycle.py` | 1,746 | Yes | Execution lifecycle |
| `substrate/spec_validation.py` | 1,483 | No | Spec validation framework |
| `substrate/replay_validation.py` | 1,034 | No | Replay safety validation |
| `substrate/pipeline_execution.py` | 758 | Yes | Pipeline execution |
| `execution/harness.py` | 707 | No | Execution harness |
| `substrate/llm_replay.py` | 619 | No | LLM replay infrastructure |
| `substrate/execution_scope.py` | 522 | Yes | Execution scoping |
| `substrate/execution_authority.py` | 501 | Yes | Execution permissions |
| `substrate/execution_result_handler.py` | 498 | No | Result handling |
| `substrate/workflow_delegation.py` | 473 | Yes | Workflow delegation |
| `execution/system_graph.py` | 472 | No | System dependency graph |
| `substrate/dispatch_enforcement.py` | 460 | No | Dispatch safety |
| `substrate/result_query.py` | 454 | Yes | Result querying |
| `substrate/execution_constraints.py` | 445 | Yes | Execution constraints |
| `substrate/pipeline.py` | 438 | No | Pipeline definition |
| `substrate/execution_adapter.py` | 415 | No | Execution adapter |
| `runtime_loop/session_registry.py` | 414 | Yes | Session registry |
| `execution/quality.py` | 409 | Yes | Quality gates |
| `substrate/execution_batch.py` | 373 | No | Batch execution |
| `adapters/execution/execution_bridge.py` | 371 | No | Execution bridge |
| `substrate/workflow_execution.py` | 361 | Yes | Workflow execution |
| `substrate/execution_worker.py` | 360 | No | Worker pool |
| `runtime_engine/execution_engine.py` | 358 | Yes | Execution engine |
| `substrate/event_scheduler.py` | 351 | Yes | Event scheduling |
| `execution/contract.py` | 351 | Yes | Execution contracts |
| `runtime_engine/execution_spine.py` | 316 | Yes | CANONICAL RUNTIME |
| `substrate/execution_control.py` | 334 | Yes | Execution control |
| `execution/system_registry.py` | 323 | No | System registry |
| `substrate/workflow_driver.py` | 309 | No | Workflow driver |
| `substrate/event_log_runtime.py` | 246 | Yes | Event logging |
| `substrate/result_store.py` | 245 | Yes | Result persistence |
| `substrate/event_store.py` | 223 | Yes | Event persistence |
| `runtime_engine/execution_budget.py` | 221 | Yes | Execution budgeting |
| `substrate/execution_router.py` | 219 | Yes | Execution routing |
| `substrate/remote_executor.py` | 216 | No | Remote execution |
| `substrate/event_spine.py` | 206 | Yes | Event spine |
| `runtime_engine/execution_credit.py` | 454 | No | Execution credit tracking |

(Plus ~30 more smaller files in stages/, runtime_loop/, adapters/execution/, protocols/)

**Current State:** Heavily used. execution_spine.py and gateway.py are CONFIRMED WORKING production infrastructure. The pipeline and lifecycle layers are active. Unreachable files represent the next-gen batch execution, replay validation, and remote execution capabilities.

**Why It Matters:** This is the engine that makes everything else run. The unreachable files (spec_validation, replay_validation, llm_replay, remote_executor) represent the ability to validate execution safety, replay decisions for debugging, and execute across machines.

**Phase:** Phase 1 (core active now) through Phase 3 (remote execution, replay)

**Recommendation:** Preserve all. The spec_validation and replay_validation files (2,517 lines) are test infrastructure that will be critical for production safety.

**Risk of Deletion:** CATASTROPHIC for gateway/execution_spine; HIGH for replay/validation/remote executor

---

## Area 9: Operator Presence / Rituals / Day Lifecycle

**Files (37 total, ~16,000 lines):**

| File | Lines | Reachable | Notes |
|---|---|---|---|
| `runtime_engine/orchestrator.py` | 1,905 | Yes | CONFIRMED WORKING |
| `substrate/discord_text_transport.py` | 1,683 | Yes | Text I/O transport |
| `substrate/discord_output_policy.py` | 1,480 | Yes | Output formatting/policy |
| `runtime_engine/daily_sync.py` | 606 | Yes | Daily sync routine |
| `substrate/ritual_execution_driver.py` | 591 | Yes | Ritual execution |
| `substrate/day_workflows.py` | 570 | Yes | Day lifecycle workflows |
| `substrate/interaction_archive.py` | 565 | Yes | Interaction persistence |
| `substrate/presence_runtime.py` | 534 | No | Full presence engine |
| `substrate/daily_rituals.py` | 513 | Yes | Ritual definitions |
| `substrate/operator_transitions.py` | 481 | Yes | State machine transitions |
| `substrate/operator_approvals.py` | 429 | No | Approval workflows |
| `substrate/message_framing.py` | 421 | Yes | Message context |
| `substrate/operator_state.py` | 393 | Yes | Operator state tracking |
| `substrate/discord_ingress_adapter.py` | 373 | Yes | Discord input processing |
| `substrate/operator_delivery.py` | 370 | No | Multi-channel delivery |
| `substrate/lifecycle_handlers.py` | 353 | Yes | Lifecycle event handlers |
| `substrate/ritual_body.py` | 341 | Yes | Ritual content generation |
| `substrate/operator_trace.py` | 336 | Yes | Operator audit trail |
| `substrate/discord_mode_routing.py` | 335 | Yes | Mode-based routing |
| `substrate/context_lifecycle.py` | 313 | Yes | Context lifecycle |
| `substrate/operator_session.py` | 299 | Yes | Operator session |
| `substrate/presence_state.py` | 293 | Yes | Presence state tracking |
| `substrate/operator_artifacts.py` | 272 | No | Artifact management |
| `substrate/mode_behavior.py` | 256 | Yes | Mode behavior rules |
| `substrate/conversation_router.py` | 246 | Yes | Conversation routing |
| `substrate/scene_policy.py` | 243 | Yes | Scene transition rules |
| `substrate/profile_resolution.py` | 238 | Yes | Profile resolution |
| `substrate/ritual_runner.py` | 217 | Yes | Ritual scheduler/runner |
| `substrate/target_policy.py` | 213 | Yes | Target selection policy |
| `substrate/ritual_inference.py` | 198 | Yes | Ritual need detection |
| `substrate/scenes.py` | 176 | Yes | Scene definitions |
| `substrate/ritual_reconciler.py` | 174 | No | Ritual conflict resolution |
| `substrate/scene_capabilities.py` | 172 | Yes | Scene capabilities |
| `substrate/roles.py` | 155 | Yes | Role definitions |
| `substrate/operator_presence.py` | 119 | Yes | Presence detection |
| `substrate/control_commands.py` | 103 | No | Control command parser |
| `substrate/role_resolver.py` | 74 | No | Role resolution |

**Current State:** Mostly production-active. Orchestrator and daily_sync are CONFIRMED WORKING. Rituals, scenes, and operator state machine are all reachable. Unreachable files are the approval workflow, multi-channel delivery, full presence runtime, and artifact management.

**Why It Matters:** This is the "day architecture" -- the system that makes EOS feel like a partner with awareness of time, context, and rhythm. Rituals create structure (morning brief, EOD sync). Operator presence makes the AI context-aware of the human's state.

**Phase:** Phase 1 (active now) through Phase 2 (expanded rituals, approval workflows)

**Recommendation:** Preserve all. High production usage. Unreachable files are natural next features.

**Risk of Deletion:** CATASTROPHIC for orchestrator/daily_sync; HIGH for ritual/operator subsystem

---

## Area 10: Primitives / Security / Governance

**Files (29 total, ~5,200 lines):**

| File | Lines | Reachable | Notes |
|---|---|---|---|
| `runtime_engine/primitives.py` | 931 | Yes | 13 EOS primitives |
| `runtime_engine/principle_engine.py` | 516 | Yes | Principle enforcement |
| `governance/capability.py` | 461 | No | Capability governance |
| `intent/compiler_ext.py` | 433 | No | Extended intent compilation |
| `capability/registry.py` | 349 | Yes | Capability registry |
| `runtime_engine/output_validator.py` | 309 | Yes | Output validation |
| `governance/governor.py` | 307 | No | Governor framework |
| `primitives/ontological.py` | 253 | No | Ontological primitives |
| `runtime_engine/authority_engine.py` | 250 | Yes | CONFIRMED WORKING |
| `intent/compiler.py` | 199 | Yes | Intent compilation |
| `runtime_engine/accountability.py` | 188 | Yes | Accountability tracking |
| `capability/router.py` | 150 | Yes | Capability routing |
| `runtime_engine/tenant.py` | 145 | Yes | Multi-tenancy |
| `runtime_engine/quality_gate.py` | 143 | Yes | Quality enforcement |
| `governance/authority.py` | 139 | Yes | Authority definitions |
| `runtime_engine/confidentiality.py` | 118 | Yes | Confidentiality rules |
| `security/access.py` | 81 | No | Access control |
| `environments/system_context.py` | 78 | Yes | System context |
| `environments/detector.py` | 72 | No | Environment detection |
| `protocols/security.py` | 31 | No | Security protocol |
| `core/clock.py` | 16 | Yes | System clock |
| `protocols/governance.py` | 7 | No | Governance protocol |

**Current State:** Partially used. authority_engine, primitives, and principle_engine are all production-active. Governance capability and governor are complete but unreachable. The primitives/ontological.py represents the philosophical foundation layer.

**Why It Matters:** Primitives are what makes EOS EOS -- they encode the founder's operating philosophy into the system's decision-making. Authority engine prevents the AI from taking unauthorized actions. These become critical at Phase 3 when other users interact with the system.

**Phase:** Phase 1 (core active) through Phase 4 (multi-tenant governance for SaaS)

**Recommendation:** Preserve all. Governance files are critical for SaaS phase. Security/access becomes essential for multi-user.

**Risk of Deletion:** CATASTROPHIC for primitives/authority_engine; HIGH for governance layer

---

## Summary Table

| Trajectory Area | File Count | Total Lines | Phase | Risk of Deletion | Recommendation |
|---|---|---|---|---|---|
| 1. Memory / Knowledge / World Model | 36 | 12,501 | 1-4 | CATASTROPHIC | Preserve + deduplicate |
| 2. Workstation / Jarvis / Voice | 44 | 16,500 | 2-3 | CATASTROPHIC | Preserve all |
| 3. Cross-Device / Sessions / Continuity | 37 | 14,500 | 2-3 | CATASTROPHIC | Preserve all |
| 4. Perception / Auto-Task | 17 | 5,700 | 2-3 | HIGH | Preserve + deduplicate |
| 5. Meeting Intelligence | 6 | 4,464 | 2 | CATASTROPHIC | Preserve, add tests |
| 6. Goal-Directed Autonomy | 64 | 26,000 | 1-4 | CATASTROPHIC | Preserve + deduplicate |
| 7. Self-Improvement / Meta-Learning | 46 | 19,000 | 1-4 | CATASTROPHIC | Preserve + deduplicate |
| 8. Execution Infrastructure | 72 | 23,000 | 1-3 | CATASTROPHIC | Preserve all |
| 9. Operator Presence / Rituals | 37 | 16,000 | 1-2 | CATASTROPHIC | Preserve all |
| 10. Primitives / Security / Governance | 29 | 5,200 | 1-4 | CATASTROPHIC | Preserve all |

**Grand Total:** 388 files, ~142,865 lines across all trajectory areas (many files appear in multiple areas)

---

## Files That Must NEVER Be Deleted

These 30 files represent the highest strategic value across all trajectory areas. Deleting any of them would set the project back weeks to months.

| # | File | Lines | Justification |
|---|---|---|---|
| 1 | `runtime_engine/session_runtime.py` | 3,685 | Largest file in UMH. The entire session management system. |
| 2 | `substrate/meeting_intelligence.py` | 2,180 | Complete meeting AI layer -- direct revenue capability for Empyrean Studio. |
| 3 | `runtime_engine/gateway.py` | 1,839 | Main production gateway. CONFIRMED WORKING. |
| 4 | `substrate/run_lifecycle.py` | 1,746 | Execution lifecycle management for every task. |
| 5 | `runtime_engine/benchmark_env.py` | 1,636 | Only system for validating decision quality improvement over time. |
| 6 | `substrate/discord_text_transport.py` | 1,683 | Primary text I/O transport for the main interface. |
| 7 | `substrate/discord_output_policy.py` | 1,480 | Output formatting and safety for all Discord messages. |
| 8 | `substrate/spec_validation.py` | 1,483 | Execution spec validation -- future production safety net. |
| 9 | `substrate/plan_executor.py` | 1,332 | Multi-mode plan execution with V2 semantic decomposition. |
| 10 | `substrate/intent_coordinator.py` | 1,304 | Intent coordination across concurrent sessions. |
| 11 | `planning/hierarchical_planning.py` | 1,213 | Hierarchical task decomposition for complex goals. |
| 12 | `substrate/claude_session_bridge.py` | 1,160 | Bridge between EOS and Claude Code sessions. |
| 13 | `substrate/stt_producer.py` | 1,146 | Full speech-to-text pipeline for Jarvis voice. |
| 14 | `runtime_engine/knowledge_domains.py` | 1,143 | Domain knowledge structure -- institutional memory. |
| 15 | `substrate/replay_validation.py` | 1,034 | Replay safety for debugging production decisions. |
| 16 | `runtime_engine/memory.py` | 1,024 | Core agent memory system. 9 importers. |
| 17 | `substrate/meeting_transport.py` | 1,011 | Meeting audio/caption transport layer. |
| 18 | `substrate/perception.py` | 993 | Ambient sensing -- foundation for proactive behavior. |
| 19 | `world/simulation.py` | 968 | World state forward simulation for decision-making. |
| 20 | `substrate/local_control.py` | 945 | Local machine control surface for Jarvis. |
| 21 | `world/state.py` | 928 | World state representation. |
| 22 | `runtime_engine/primitives.py` | 931 | The 13 EOS primitives -- philosophical foundation. |
| 23 | `runtime_engine/evolution_engine.py` | 903 | System self-evolution -- weekly improvement cycle. |
| 24 | `substrate/station_daemon.py` | 859 | Always-on workstation daemon for local presence. |
| 25 | `goals/meta_goal.py` | 841 | Meta-goal framework -- goals about goals. |
| 26 | `runtime_engine/long_horizon_benchmark.py` | 832 | Long-term decision quality benchmarking. |
| 27 | `runtime_engine/voice_interface.py` | 825 | Voice pipeline abstraction -- voice is the primary future interface. |
| 28 | `substrate/voice_session.py` | 789 | Voice session state management. |
| 29 | `runtime_engine/multi_strategy.py` | 785 | Multi-strategy evaluation for complex decisions. |
| 30 | `persistence_layer/persistence.py` | 754 | Data persistence layer -- all state depends on this. |

---

## Quarantine Candidates

These files could be moved to `_future/` to reduce cognitive load WITHOUT losing strategic value. Criteria: (1) not production-reachable, (2) not imported by anything production-reachable, (3) represent future features beyond Phase 2.

| File | Lines | Reason for Quarantine |
|---|---|---|
| `protocols/capabilities.py` | 7 | Empty protocol stub |
| `protocols/governance.py` | 7 | Empty protocol stub |
| `protocols/interpretation.py` | 14 | Empty protocol stub |
| `protocols/planning.py` | 16 | Empty protocol stub |
| `protocols/outcome.py` | 24 | Empty protocol stub |
| `protocols/execution.py` | 25 | Empty protocol stub |
| `protocols/signals.py` | 21 | Empty protocol stub |
| `protocols/workstation.py` | 18 | Empty protocol stub |
| `protocols/security.py` | 31 | Empty protocol stub |
| `protocols/memory.py` | 31 | Empty protocol stub |
| `protocols/world.py` | 21 | Empty protocol stub |
| `adapters/null.py` | 34 | Null adapter pattern, no callers |
| `adapters/stubs.py` | 91 | Test stubs, no callers |
| `adapters/umh_goals.py` | 36 | Thin adapter, no callers |
| `adapters/umh_storage.py` | 45 | Thin adapter, no callers |
| `adapters/umh_strategy.py` | 36 | Thin adapter, no callers |
| `adapters/discord_adapter.py` | 107 | Unused Discord adapter |
| `environments/detector.py` | 72 | Environment detection, no callers |
| `interfaces/cli.py` | 164 | CLI interface, not in any service |
| `interfaces/discord/handlers/voice_handler.py` | 22 | Empty voice handler stub |
| `__main__.py` | 8 | Module entry point, unused |

**Total quarantine candidates:** 21 files, 850 lines

**DO NOT quarantine:** Any file over 200 lines, any file with even 1 importer, any file in a trajectory area that could activate in Phase 2. The quarantine list is deliberately conservative.

---

## Duplicate Cleanup Priority

The 37 duplicate file pairs between `runtime_engine/` and modular directories should be resolved. Recommended approach:

1. **Identical pairs (17):** Delete the runtime_engine copy. Update any imports pointing to runtime_engine to use the modular path.
2. **Diverged pairs (20):** Manually diff each pair. Merge changes into the modular copy. Delete the runtime_engine copy. Update imports.

This cleanup would remove approximately 10,000-12,000 lines of duplicated code without losing any functionality.

---

## Key Finding

Of 197,401 total lines in UMH, only 65,255 (33%) are unreachable from production entry points. But of those unreachable lines, approximately 40,000 represent future-trajectory code that is strategically essential (meeting intelligence, plan executor, benchmark environment, workstation subsystem, replay validation). The remaining ~25,000 unreachable lines are duplicates of production-reachable code sitting in runtime_engine/.

**The unreachable code is not dead code. It is unactivated infrastructure for the next 3 phases of the product.**

Deleting these files would save 33% of line count but destroy 80% of the project's strategic optionality.
