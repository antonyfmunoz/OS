# UMH System-Wide Essentialism Audit

**Date:** 2026-04-25
**Scope:** All 529 Python files in `umh/`
**Standard:** Canonical execution path validation
**Method:** Per-file classification using 10-question rubric + import graph analysis + 4 parallel audit agents

---

## Classification Summary

| Classification | Count | % | Description |
|---|---|---|---|
| **CORE** | 56 | 10.6% | Removal breaks the canonical execution path |
| **MVP** | 138 | 26.1% | Required for current working product |
| **FUTURE** | 316 | 59.7% | Aligned with trajectory but not production-critical |
| **DELETE** | 19 | 3.6% | Dead code, duplicates, or broken imports |

**Total: 529 files. 194 files (36.7%) are production-essential. 316 files (59.7%) are frozen future infrastructure.**

---

## 1. CORE Files (56) — Removal Breaks the Spine

### Execution Engine (9)
| File | Purpose |
|---|---|
| `execution/__init__.py` | Package namespace |
| `execution/contract.py` | ExecutionRequest/Result types, enums |
| `execution/engine.py` | `execute()`, `dispatch_prompt()`, `lightweight_execute()` |
| `execution/interfaces.py` | Backend/Observer protocols + singleton management |
| `execution/pipeline.py` | ExecutionPipeline — ordered stage runner |
| `execution/runtime.py` | RuntimeResult, RateLimiter, calculate_cost |
| `execution/stages.py` | StageContext, ExecutionStage protocol |
| `execution/quality.py` | QualityGate — 4-lens transformation scoring |
| `execution/harness.py` | AgentHarness multi-step orchestrator |

### Pipeline Stages (7)
| File | Purpose |
|---|---|
| `stages/__init__.py` | Package namespace |
| `stages/authority.py` | Stage 1: Authority gatekeeper |
| `stages/enhancement.py` | Stage 2: Trust-adjusted prompt expansion |
| `stages/context_assembly.py` | Stage 3: System prompt extraction |
| `stages/llm_generation.py` | Stage 4: LLM call via model_router |
| `stages/commit.py` | Stage 6: Persist response (memory, knowledge, feedback, world) |
| `stages/footer.py` | Stage 7: Response footer (model/cost/token display) |

### Gateway (2)
| File | Purpose |
|---|---|
| `gateway/__init__.py` | Re-exports UMHInput, UMHOutput, translate_and_run |
| `gateway/entry.py` | UMHInput/UMHOutput contracts, translate_and_run, utility_llm_call |

### Adapters (8)
| File | Purpose |
|---|---|
| `adapters/__init__.py` | Package namespace |
| `adapters/base.py` | Protocol definitions + adapter registry |
| `adapters/bridge.py` | discover_platform_adapter() — dynamic import |
| `adapters/contracts.py` | AdapterContext + Adapter protocol for event dispatch |
| `adapters/registry.py` | Central adapter lookup with deterministic ordering |
| `adapters/event_router.py` | Bridges SchedulerEvents to adapters |
| `adapters/model_router.py` | Multi-provider LLM router (Anthropic/Gemini/Groq/Perplexity/Ollama) |
| `adapters/llm.py` | OllamaLLMAdapter + HttpLLMAdapter |

### Runtime Engine (17)
| File | Purpose | Importers |
|---|---|---|
| `runtime_engine/agent_hierarchy.py` | Org chart: Founder→EA→CEO→Departments | 3 |
| `runtime_engine/agent_runtime.py` | Agent dispatch, skill loading, LLM calls | 26 |
| `runtime_engine/authority_engine.py` | 4 risk class governance | 6 |
| `runtime_engine/cc_sdk.py` | Claude Code Agent SDK wrapper | 2 |
| `runtime_engine/commit_pipeline.py` | Post-generation commit stages 6-10 | 2 |
| `runtime_engine/context_builder.py` | Single-pass context assembly | 13 |
| `runtime_engine/db.py` | Neon connection layer | 1 |
| `runtime_engine/event_bus.py` | Reactive coordination pub/sub | 7 |
| `runtime_engine/execution_spine.py` | Production execution spine + SpineResult | 13 |
| `runtime_engine/gateway.py` | Single control plane entry point | 11 |
| `runtime_engine/memory.py` | Agent memory backed by Neon | 29 |
| `runtime_engine/model_preferences.py` | Multi-model routing + business context | 3 |
| `runtime_engine/model_router.py` | LLM provider routing (Gemini/Ollama/CC SDK) | 11 |
| `runtime_engine/orchestrator.py` | Strategic intelligence + morning brief | 5 |
| `runtime_engine/primitives.py` | Stage-aware business rules engine | 9 |
| `runtime_engine/skill_registry.py` | Skill loading + matching | 5 |
| `runtime_engine/venture_knowledge.py` | Venture business data | 11 |

### Substrate (9)
| File | Purpose |
|---|---|
| `substrate/__init__.py` | Public API surface (43 module re-exports) |
| `substrate/storage.py` | KV persistence (JSON + optional Neon) |
| `substrate/event_scheduler.py` | FIFO event queue + subscriber registry |
| `substrate/runtime_state_store.py` | In-memory state with deterministic mutations |
| `substrate/event_log_runtime.py` | Append-only JSONL event log |
| `substrate/checkpoint_runtime.py` | Durable checkpoint snapshots |
| `substrate/runtime_rehydration.py` | State rebuild from checkpoint + log replay |
| `substrate/runtime_bootstrap.py` | Singleton getters for event log/checkpoint/store |
| `substrate/execution_contract.py` | Execution boundary types |

### Storage (4)
| File | Purpose |
|---|---|
| `storage/__init__.py` | Re-exports StorageBackend + InMemoryStorage |
| `storage/backend.py` | StorageBackend protocol + InMemoryStorage |
| `storage/adapters/__init__.py` | Package namespace |
| `storage/adapters/neon.py` | Neon PostgreSQL connection with RLS (40+ importers) |

### Interfaces (2)
| File | Purpose |
|---|---|
| `interfaces/__init__.py` | Package namespace |
| `interfaces/cli.py` | UMH CLI (status, run, capabilities, adapters, trace) |

### Small Domain Modules (on canonical path — 13)
| File | Purpose | Why CORE |
|---|---|---|
| `context/builder.py` | ContextBuilder — fault-isolated, priority-aware | Imported by execution/engine.py |
| `context/types.py` | Immutable context value objects | Imported by execution/engine.py |
| `core/__init__.py` | Package namespace | |
| `core/clock.py` | Monotonic clock utilities | Imported by execution/pipeline.py |
| `environments/system_context.py` | Runtime identity and environment config | 53 external importers |
| `governance/authority.py` | Safety and permission gating | Imported by gateway/entry.py |
| `memory/storage.py` | UMH StorageBackend re-export | Imported by storage/__init__.py |
| `signal/types.py` | Domain-independent signal classification | Imported by run.py + protocols |
| `world/model.py` | World model state | Imported by stages/commit.py |

### Root (3)
| File | Purpose |
|---|---|
| `__init__.py` | Public API: `from umh import run` |
| `__main__.py` | CLI entry point → interfaces/cli.py |
| `run.py` | UMH 9-stage run loop |

---

## 2. MVP Files (138) — Current Working Product

### Runtime Engine (42)
`accountability.py`, `agent_teams.py`, `ai_identity.py`, `ceo_agent.py`, `ceo_intelligence.py`, `ceo_operational_standards.py`, `claude_skill_registry.py`, `confidentiality.py`, `context_compaction.py`, `coordination_engine.py`, `daily_sync.py`, `decision_log.py`, `delegation_tracker.py`, `discord_utils.py`, `ea_operational_standards.py`, `email_gps.py`, `embedding_engine.py`, `evolution_engine.py`, `execution_engine.py`, `feedback_loop.py`, `founder_rate.py`, `gws_connector.py`, `human_intelligence.py`, `input_intelligence.py`, `intent_router.py`, `knowledge_domains.py`, `knowledge_graph.py`, `knowledge_integrator.py`, `martell_patterns.py`, `notebooklm_sync.py`, `notion_publisher.py`, `onboarding_backfill.py`, `output_validator.py`, `portfolio_advisor.py`, `portfolio_advisor_standards.py`, `principle_engine.py`, `proactive_engine.py`, `quality_gate.py`, `reality_context.py`, `reality_engine.py`, `research_engine.py`, `self_awareness.py`, `session_state.py`, `session_store.py`, `signal_hierarchy.py`, `skill_improvement.py`, `stage_manager.py`, `status.py`, `strategy_engine.py`, `tenant.py`, `user_model.py`, `voice_engine.py`, `voice_interface.py`, `world_pulse.py`

### Interfaces (19)
`interfaces/discord/__init__.py`, `interfaces/discord/bot.py` (5339L — primary user interface), `interfaces/discord/dm_monitor.py`, `interfaces/discord/handlers/__init__.py`, `interfaces/discord/handlers/cc_command_handler.py`, `interfaces/discord/handlers/intent_handler.py`, `interfaces/discord/handlers/pipeline_handler.py`, `interfaces/discord/substrate/__init__.py`, `interfaces/discord/substrate/attachment_fallback.py`, `interfaces/discord/substrate/delivery_policy.py`, `interfaces/telegram/__init__.py`, `interfaces/telegram/bot.py`, `interfaces/webhooks/__init__.py`, `interfaces/webhooks/calendly.py`, `interfaces/webhooks/cc_receiver.py`

### Substrate (57)
**Discord transport:** `discord_text_transport.py`, `discord_mode_routing.py`, `discord_output_policy.py`, `session_discord_bridge.py`, `session_watcher.py`, `session_control.py`, `claude_session_bridge.py`, `claude_responder.py`, `message_framing.py`, `tts_sanitize.py`, `mode_behavior.py`, `capability_tagging.py`, `target_policy.py`

**Event system:** `event_spine.py`, `event_store.py`, `interaction_archive.py`, `execution_trace.py`

**Lifecycle:** `run_lifecycle.py`, `run_execution.py`, `day_workflows.py`, `daily_rituals.py`, `ritual_body.py`, `ritual_runner.py`, `ritual_execution_driver.py`, `operator_session.py`, `operator_trace.py`, `operator_delivery.py`, `operator_artifacts.py`

**Station:** `nodes.py`, `actions.py`, `station.py`, `station_bus.py`, `station_daemon.py`, `station_helpers.py`, `station_drainer.py`, `station_presence.py`, `result_store.py`

**Task system:** `task_system.py`, `task_pipeline.py`, `task_decomposition.py`, `task_execution.py`

**Orchestration:** `decision_engine.py`, `decision_events.py`, `planner.py`, `planner_events.py`, `intent_models.py`, `intent_coordinator.py`, `intent_memory.py`, `plan_registry.py`, `plan_scoring.py`, `plan_mutation.py`, `score_meta.py`, `autonomy_policy.py`, `orchestration_bootstrap.py`, `orchestration_mode.py`, `workflow_driver.py`, `trigger_adapters.py`, `lifecycle_handlers.py`

**Execution fabric:** `execution_authority.py`, `execution_adapter.py`, `execution_worker.py`, `execution_result_handler.py`, `execution_events.py`, `execution_router.py`, `execution_bootstrap.py`, `execution_batch.py`, `artifact_contract.py`, `rituals.py`

### Adapters (3)
`adapters/provider_health.py`, `adapters/stubs.py`, `adapters/umh_storage.py`

### Small Domain Modules (17)
| File | Classification Rationale |
|---|---|
| `capability/registry.py` | Imported by run.py, feedback/loop.py |
| `capability/router.py` | Imported by run.py, harness |
| `context/__init__.py` | Package namespace |
| `decision/trace.py` | 10 external importers (shim hub) |
| `environments/__init__.py` | Package namespace |
| `environments/detector.py` | Used by workstation/profile.py |
| `feedback/__init__.py` | Package namespace |
| `feedback/loop.py` | Imported by run.py |
| `feedback/outcome_evaluator.py` | Imported by stages/outcome.py |
| `goals/__init__.py` | Package namespace |
| `goals/state.py` | 16 external importers (foundation goal type) |
| `governance/__init__.py` | Package namespace |
| `governance/capability.py` | Used by execution/harness.py |
| `intent/compiler.py` | Imported by run.py |
| `memory/__init__.py` | Package namespace |
| `memory/embedder.py` | Imported by runtime_engine/memory.py |
| `runtime_loop/session_registry.py` | 3 ext importers (bot.py, cc_receiver, intent_handler) |
| `runtime_loop/input_router.py` | 2 ext importers (bot.py, voice_loop) |
| `runtime_loop/live_loop.py` | 1 ext importer (bot.py) |
| `runtime_loop/output_dispatcher.py` | 1 ext importer (cc_receiver.py) |
| `runtime_loop/session_router.py` | 1 ext importer (bot.py) |
| `runtime_loop/surface_registry.py` | 1 ext importer (bot.py) |
| `signal/event_bus.py` | 3 ext importers |
| `signal/ingest.py` | Imported by run.py |
| `workstation/business.py` | 16 external importers |
| `world/substrate.py` | 13 external importers |

---

## 3. FUTURE Files (316) — Frozen Infrastructure

### Cluster Breakdown

| Cluster | Count | Description |
|---|---|---|
| Meta-harness / Session Runtime | 57 | `session_runtime` → `session_interface` layer; built ahead of need |
| Benchmark / Test infrastructure | 16 | Self-contained validation environment for meta-harness |
| Voice / Audio pipeline | 17 | STT/TTS/Wake/PTT/Discord voice, meeting intelligence |
| Meeting intelligence | 5 | Google Meet transcript + intervention |
| Local control / OS | 6 | Mouse/keyboard, browser automation, app allowlist |
| Workstation / Station extras | 15 | Control layer, remote executor, node transport, presence |
| Goals / Reasoning / Analytics | 55 | Goal arbitration, causal credit, counterfactual eval, meta-control |
| Planning / Policy / Strategy | 12 | Directive engine, hierarchical planning, foresight, regime |
| Protocols layer | 13 | Protocol definitions (tiny, 242 total lines) |
| Orchestration extras | 20 | LLM planner, replay, composition, pipeline execution |
| Sessions / Continuity / Profiles | 9 | Runtime session, continuity, presence state |
| Live sessions | 4 | Transport-agnostic live session model |
| Perception / Auto-task | 2 | Ambient sensing + auto task generation |
| Scenes | 3 | Workstation bootstrap recipes |
| Adapters (future) | 9 | Discord/Notion/Voice/STT/TTS adapters, goals/strategy persistence |
| Small domain modules | 40+ | Off-path feedback, goals, signal, world, security, primitives |

### Notable Future Files
| File | Lines | Notes |
|---|---|---|
| `goals/` (12 non-init files) | 4,779 | Massive goal system; only goals/state.py used externally |
| `reasoning/` (15 files) | 5,678 | Full causal reasoning stack; only used by session_runtime |
| `analytics/` (9 files) | 3,619 | Strategy analytics; only used by session_runtime + benchmark |
| `world/` (7 of 8 files) | 3,755 | Full world simulation; only world/model.py is CORE |
| `protocols/` (13 files) | 242 | Tiny protocol defs; only 2 external importers total |
| `primitives/ontological.py` | 253 | Zero external importers |
| `security/access.py` | 81 | Zero external importers |

---

## 4. DELETE Candidates (19)

### Dead Duplicates (4)
| File | Reason |
|---|---|
| `execution/system_graph.py` | Exact duplicate of `runtime_engine/system_graph.py`; zero prod importers |
| `execution/system_registry.py` | Exact duplicate of `runtime_engine/system_registry.py`; zero prod importers |
| `execution/system_selector.py` | Exact duplicate of `runtime_engine/system_selector.py`; zero prod importers |
| `adapters/workstation_adapter.py` | Exact duplicate of `adapters/execution/workstation_adapter.py` |

### Deprecated (1)
| File | Reason |
|---|---|
| `runtime_engine/cognitive_loop.py` | Deprecated 2026-04-21. Only shim for `format_response_footer`. Rewire `context_builder.py` to import from `execution_spine.py` directly, then delete. |

### Broken Imports — Missing Modules (3 missing files referenced)
| Missing Module | Importers | Impact |
|---|---|---|
| `substrate/workflow_events` | `trigger_adapters.py`, `workflow_driver.py`, `intent_coordinator.py` | ImportError at runtime — 3 MVP orchestration files broken |
| `substrate/task_finalization` | `bot.py`, `cc_receiver.py` | Lazy import — fails when code path hit |
| `substrate/session_readiness` | `cc_receiver.py` | Lazy import — fails when code path hit |

### Null/Test-Only (11 — delete or consolidate)
| File | Reason |
|---|---|
| `adapters/null.py` | Convenience re-export for tests only |
| `adapters/execution/workstation_adapter.py` | Tests only; keep this OR parent, not both |
| `adapters/execution/batch_drainer.py` | Zero prod importers, tests only |
| `adapters/execution/execution_bridge.py` | Zero prod importers, tests only |
| `runtime_engine/action_synthesis.py` | Zero prod importers, 1 test |
| `runtime_engine/fabric_analytics.py` | Zero prod importers, 1 test |
| `runtime_engine/causal_credit.py` | Zero importers outside self |
| `runtime_engine/outcome_feedback.py` | Zero prod importers, 2 tests |
| `runtime_engine/strategy_mutation.py` | Zero prod importers, 1 test |
| `runtime_engine/strategy_pattern_memory.py` | Zero prod importers, 1 test |
| `runtime_engine/plan_mutation.py` | Zero prod importers, 1 test (distinct from substrate/plan_mutation.py which IS used) |

---

## 5. Refactor-Later Candidates

| File / Area | Issue | Priority |
|---|---|---|
| `runtime_engine/gateway.py` | Imports 28+ modules directly — fattest dependency node | MEDIUM |
| `runtime_engine/agent_runtime.py` | Directly instantiates `anthropic.Anthropic()` instead of routing through model_router | LOW |
| `interfaces/discord/bot.py` | 5,339 lines — needs handler extraction | LOW |
| `substrate/__init__.py` | 821 lines, 43 re-exports — heaviest init in codebase | LOW |
| `runtime_engine/cognitive_loop.py` | Deprecated shim — one import to rewire then delete | HIGH |
| `decision/trace.py` | 1,066-line shim hub — 10 importers use it as compatibility layer for 8+ runtime_engine files | MEDIUM |

---

## 6. Confirmed Runtime Execution Map

```
[Discord/Telegram/CLI/Webhook]
        │
        ▼
  gateway/entry.py  ← translate_and_run() / utility_llm_call()
        │
        ▼
  runtime_engine/gateway.py  ← route to domain handler
        │
        ▼
  execution/engine.py  ← execute() / lightweight_execute()
        │
        ▼
  execution/pipeline.py  ← ExecutionPipeline.run()
        │
        ├── stages/authority.py      ← Stage 1: permission gate
        ├── stages/enhancement.py    ← Stage 2: prompt expansion
        ├── stages/context_assembly.py ← Stage 3: system prompt
        ├── stages/llm_generation.py ← Stage 4: LLM call
        │       └── runtime_engine/model_router.py
        │               └── adapters/model_router.py
        ├── stages/quality.py        ← Stage 5a: quality loop
        ├── stages/stage_filter.py   ← Stage 5b: advice filter
        ├── stages/outcome.py        ← Stage 5c: outcome eval
        ├── stages/commit.py         ← Stage 6: persist
        │       └── runtime_engine/commit_pipeline.py
        │               ├── runtime_engine/memory.py
        │               ├── runtime_engine/knowledge_integrator.py
        │               ├── runtime_engine/feedback_loop.py
        │               └── world/model.py
        └── stages/footer.py         ← Stage 7: response footer
        │
        ▼
  execution/contract.py  ← ExecutionResult
        │
        ▼
  [Response returned to interface]
```

### Alternative Entry Points
- `run.py` → `run()` — 9-stage meta-harness run loop (imports from 12 domain modules)
- `runtime_engine/execution_spine.py` → `run_via_umh()` — legacy bridge that builds pipeline inline
- `gateway/entry.py` → `utility_llm_call()` — lightweight LLM call (routes through `lightweight_execute()`)

---

## 7. Bypass Paths Discovered

Files that call `model_router.call_with_fallback()` directly, bypassing the `execute()` pipeline:

| File | Bypass Method | Justification |
|---|---|---|
| `runtime_engine/email_gps.py` | 4 direct calls to model_router | Speed — email processing skips pipeline overhead |
| `runtime_engine/world_pulse.py` | 1 direct call | Background intelligence — no user-facing pipeline needed |
| `runtime_engine/ceo_agent.py` | 1 direct call | CEO agent strategy — force_opus bypass |
| `runtime_engine/multi_strategy.py` | 1 direct call | Candidate generation — intentional multi-call |
| `substrate/voice_eos_responder.py` | 1 direct call | Documented: avoids DB writes, approval gates, memory writes |
| `substrate/meeting_intelligence.py` | 2 direct calls | Rolling summary + intervention phrasing |
| `interfaces/discord/dm_monitor.py` | Creates `genai.Client` directly | True bypass — raw Gemini Vision for screenshot OCR |
| `interfaces/discord/bot.py` | `utility_llm_call()` | Through gateway utility path, not `execute()` |
| `interfaces/discord/handlers/cc_command_handler.py` | `utility_llm_call()` | Followup drafting, date parsing |
| `interfaces/discord/handlers/intent_handler.py` | `utility_llm_call()` | Intent classification |
| `interfaces/webhooks/calendly.py` | `utility_llm_call()` | Follow-up email drafting |
| `runtime_engine/agent_runtime.py` | Direct `anthropic.Anthropic()` | Legacy fallback — should route through model_router |

**12 files with bypass paths. 1 true provider bypass (dm_monitor.py creates raw genai.Client). 1 legacy bypass (agent_runtime.py creates raw Anthropic client). 5 use model_router directly. 5 use utility_llm_call (which goes through gateway but not execute()).**

---

## 8. Recommended Next Actions

### Immediate (debt reduction)
1. **Delete 4 duplicate files** — `execution/system_{graph,registry,selector}.py` + `adapters/workstation_adapter.py`
2. **Rewire cognitive_loop.py** — Move `format_response_footer` import in context_builder.py to execution_spine.py, delete cognitive_loop.py
3. **Fix 3 missing modules** — Create stubs or remove imports for `substrate/workflow_events`, `substrate/task_finalization`, `substrate/session_readiness`

### Short-term (architectural hygiene)
4. **Fix agent_runtime.py Anthropic bypass** — Route through model_router instead of direct `anthropic.Anthropic()` instantiation
5. **Fix dm_monitor.py genai bypass** — Route Gemini Vision through model_router or a dedicated vision routing function
6. **Evaluate 11 zero-importer runtime_engine files** — Consider moving to a `runtime_engine/_future/` subdirectory or deleting if tests don't add value

### Medium-term (structural)
7. **Split gateway.py** (28 direct imports) — Extract domain dispatch into separate route files
8. **Split bot.py** (5,339 lines) — Continue handler extraction started with handlers/ subdirectory
9. **Slim substrate/__init__.py** (821 lines, 43 re-exports) — Use lazy imports or split into sub-packages

### Strategic (freeze boundary)
10. **Draw a freeze line** — The 316 FUTURE files represent ~60% of the codebase by file count. Consider moving meta-harness files into a `umh/_future/` directory to make the production boundary explicit and reduce cognitive load.

---

## Appendix: Complete File-by-Directory Classification

<details>
<summary>execution/ (12 files)</summary>

| File | Classification |
|---|---|
| `__init__.py` | CORE |
| `contract.py` | CORE |
| `engine.py` | CORE |
| `harness.py` | CORE |
| `interfaces.py` | CORE |
| `pipeline.py` | CORE |
| `quality.py` | CORE |
| `runtime.py` | CORE |
| `stages.py` | CORE |
| `system_graph.py` | DELETE |
| `system_registry.py` | DELETE |
| `system_selector.py` | DELETE |

</details>

<details>
<summary>stages/ (9 files)</summary>

| File | Classification |
|---|---|
| `__init__.py` | CORE |
| `authority.py` | CORE |
| `commit.py` | CORE |
| `context_assembly.py` | CORE |
| `enhancement.py` | CORE |
| `footer.py` | CORE |
| `llm_generation.py` | CORE |
| `outcome.py` | MVP |
| `quality.py` | MVP |
| `stage_filter.py` | MVP |

</details>

<details>
<summary>gateway/ (2 files)</summary>

| File | Classification |
|---|---|
| `__init__.py` | CORE |
| `entry.py` | CORE |

</details>

<details>
<summary>adapters/ (26 files)</summary>

| File | Classification |
|---|---|
| `__init__.py` | CORE |
| `base.py` | CORE |
| `bridge.py` | CORE |
| `contracts.py` | CORE |
| `event_router.py` | CORE |
| `llm.py` | CORE |
| `model_router.py` | CORE |
| `registry.py` | CORE |
| `provider_health.py` | MVP |
| `stubs.py` | MVP |
| `umh_storage.py` | MVP |
| `null.py` | DELETE |
| `discord_adapter.py` | FUTURE |
| `notion_adapter.py` | FUTURE |
| `umh_goals.py` | FUTURE |
| `umh_strategy.py` | FUTURE |
| `voice_adapter.py` | FUTURE |
| `voice_loop.py` | FUTURE |
| `voice_state.py` | FUTURE |
| `stt_engine.py` | FUTURE |
| `tts_engine.py` | FUTURE |
| `workstation_adapter.py` | DELETE |
| `execution/__init__.py` | CORE |
| `execution/workstation_adapter.py` | FUTURE |
| `execution/batch_drainer.py` | FUTURE |
| `execution/execution_bridge.py` | FUTURE |

</details>

<details>
<summary>runtime_engine/ (146 files)</summary>

| File | Classification |
|---|---|
| `agent_hierarchy.py` | CORE |
| `agent_runtime.py` | CORE |
| `authority_engine.py` | CORE |
| `cc_sdk.py` | CORE |
| `commit_pipeline.py` | CORE |
| `context_builder.py` | CORE |
| `db.py` | CORE |
| `event_bus.py` | CORE |
| `execution_spine.py` | CORE |
| `gateway.py` | CORE |
| `memory.py` | CORE |
| `model_preferences.py` | CORE |
| `model_router.py` | CORE |
| `orchestrator.py` | CORE |
| `primitives.py` | CORE |
| `skill_registry.py` | CORE |
| `venture_knowledge.py` | CORE |
| `accountability.py` | MVP |
| `agent_teams.py` | MVP |
| `ai_identity.py` | MVP |
| `ceo_agent.py` | MVP |
| `ceo_intelligence.py` | MVP |
| `ceo_operational_standards.py` | MVP |
| `claude_skill_registry.py` | MVP |
| `confidentiality.py` | MVP |
| `context_compaction.py` | MVP |
| `coordination_engine.py` | MVP |
| `daily_sync.py` | MVP |
| `decision_log.py` | MVP |
| `delegation_tracker.py` | MVP |
| `discord_utils.py` | MVP |
| `ea_operational_standards.py` | MVP |
| `email_gps.py` | MVP |
| `embedding_engine.py` | MVP |
| `evolution_engine.py` | MVP |
| `execution_engine.py` | MVP |
| `feedback_loop.py` | MVP |
| `founder_rate.py` | MVP |
| `gws_connector.py` | MVP |
| `human_intelligence.py` | MVP |
| `input_intelligence.py` | MVP |
| `intent_router.py` | MVP |
| `knowledge_domains.py` | MVP |
| `knowledge_graph.py` | MVP |
| `knowledge_integrator.py` | MVP |
| `martell_patterns.py` | MVP |
| `notebooklm_sync.py` | MVP |
| `notion_publisher.py` | MVP |
| `onboarding_backfill.py` | MVP |
| `output_validator.py` | MVP |
| `portfolio_advisor.py` | MVP |
| `portfolio_advisor_standards.py` | MVP |
| `principle_engine.py` | MVP |
| `proactive_engine.py` | MVP |
| `quality_gate.py` | MVP |
| `reality_context.py` | MVP |
| `reality_engine.py` | MVP |
| `research_engine.py` | MVP |
| `self_awareness.py` | MVP |
| `session_state.py` | MVP |
| `session_store.py` | MVP |
| `signal_hierarchy.py` | MVP |
| `skill_improvement.py` | MVP |
| `stage_manager.py` | MVP |
| `status.py` | MVP |
| `strategy_engine.py` | MVP |
| `tenant.py` | MVP |
| `user_model.py` | MVP |
| `voice_engine.py` | MVP |
| `voice_interface.py` | MVP |
| `world_pulse.py` | MVP |
| `cognitive_loop.py` | DELETE |
| `action_synthesis.py` | DELETE |
| `fabric_analytics.py` | DELETE |
| `causal_credit.py` | DELETE |
| `outcome_feedback.py` | DELETE |
| `strategy_mutation.py` | DELETE |
| `strategy_pattern_memory.py` | DELETE |
| `plan_mutation.py` | DELETE |
| *(remaining 72 files)* | FUTURE |

</details>

<details>
<summary>substrate/ (157 files)</summary>

| Classification | Count |
|---|---|
| CORE | 9 |
| MVP | 57 |
| FUTURE | 88 |
| DELETE | 3 (missing modules referenced) |

See Section 4 for DELETE details. Full file list in agent output.

</details>

<details>
<summary>interfaces/ (15 files)</summary>

| File | Classification |
|---|---|
| `__init__.py` | CORE |
| `cli.py` | CORE |
| `discord/__init__.py` | MVP |
| `discord/bot.py` | MVP |
| `discord/dm_monitor.py` | MVP |
| `discord/handlers/__init__.py` | MVP |
| `discord/handlers/cc_command_handler.py` | MVP |
| `discord/handlers/intent_handler.py` | MVP |
| `discord/handlers/pipeline_handler.py` | MVP |
| `discord/handlers/voice_handler.py` | FUTURE |
| `discord/substrate/__init__.py` | MVP |
| `discord/substrate/attachment_fallback.py` | MVP |
| `discord/substrate/delivery_policy.py` | MVP |
| `telegram/__init__.py` | MVP |
| `telegram/bot.py` | MVP |
| `webhooks/__init__.py` | MVP |
| `webhooks/calendly.py` | MVP |
| `webhooks/cc_receiver.py` | MVP |
| `webhooks/higgsfield.py` | FUTURE |

</details>

<details>
<summary>storage/ (4 files)</summary>

All CORE. See CORE section above.

</details>

<details>
<summary>Small domain modules (25 directories, ~141 files)</summary>

**On canonical path (mixed CORE/MVP/FUTURE):**
- `capability/`: registry (MVP), router (MVP)
- `context/`: builder (CORE), types (CORE), budget (FUTURE)
- `core/`: clock (CORE)
- `decision/`: trace (MVP — 10 ext importers, shim hub)
- `environments/`: system_context (CORE — 53 ext importers), detector (MVP)
- `feedback/`: loop (MVP), outcome_evaluator (MVP), dynamics (FUTURE), outcome_feedback (FUTURE)
- `goals/`: state (MVP — 16 ext importers), interfaces (FUTURE), all others FUTURE
- `governance/`: authority (CORE), capability (MVP), governor (FUTURE)
- `intent/`: compiler (MVP), compiler_ext (FUTURE)
- `memory/`: storage (CORE), embedder (MVP), store (FUTURE)
- `signal/`: types (CORE), event_bus (MVP), ingest (MVP), router (FUTURE), hierarchy (FUTURE), sensitivity (FUTURE)
- `world/`: model (CORE), substrate (MVP — 13 ext importers), all others FUTURE

**Off canonical path (all FUTURE):**
- `actions/` (3 files): FUTURE
- `analytics/` (9 files): FUTURE
- `objectives/` (1 file): FUTURE
- `persistence_layer/` (2 files): FUTURE
- `planning/` (3 files): FUTURE
- `policy/` (4 files): FUTURE
- `primitives/` (1 file): FUTURE (zero ext importers)
- `protocols/` (13 files): FUTURE (2 ext importers total, 242 lines total)
- `reasoning/` (15 files): FUTURE
- `runtime_loop/`: session_registry (MVP), input_router (MVP), live_loop (MVP), output_dispatcher (MVP), session_router (MVP), surface_registry (MVP), remaining 6 files FUTURE
- `security/` (1 file): FUTURE (zero ext importers)
- `strategy/` (2 files): FUTURE
- `workstation/`: business (MVP — 16 ext importers), profile (FUTURE)

</details>
