# Controlled Collapse Ledger — Into UMH

**Started:** 2026-04-24
**Safety tag:** `pre-controlled-collapse-umh` (on commit 67b619d)
**Uncommitted changes at start:** 8775 files (mostly _holding migration)

## Purpose

Track every file moved, copied, deleted, quarantined, or shimmed during
the controlled collapse of this repo into a single productized UMH.

## Ownership Model

| Category | Description |
|----------|-------------|
| UMH_CORE | Pure harness: intelligence, world model, context, planning, execution, governance, memory, feedback, capability, adapters |
| UMH_INTERFACE_PROTOTYPE | Discord, Notion, voice, CLI, workstation/Jarvis surfaces |
| UMH_TOOL_HARNESSING | Claude Code skills, OpenClaw, tool mastery, agent instructions |
| UMH_INSTANCE_DATA | Data from using/testing the harness |
| NON_UMH_PRODUCT_OR_NOISE | SaaS UI, stale scratch, generated junk, obsolete logs |

## UMH State at Start

| Module | Status |
|--------|--------|
| umh/run.py | Live — 9-stage run loop |
| umh/execution/harness.py | Live — AgentHarness extracted from legacy |
| umh/execution/engine.py | Live — ExecutionBackend dispatch |
| umh/execution/contract.py | Live — ExecutionRequest/Result types |
| umh/execution/interfaces.py | Live — Backend/Observer protocols |
| umh/execution/pipeline.py | Live — composable stage pipeline |
| umh/execution/stages.py | Live — StageContext + ExecutionStage protocol |
| umh/capability/registry.py | Live — Capability registry |
| umh/capability/router.py | Live — multi-dimensional routing |
| umh/governance/authority.py | Live — GovernancePolicy + authority levels |
| umh/memory/storage.py | Live — StorageBackend protocol |
| umh/context/builder.py | Live — ContextBuilder |
| umh/context/types.py | Live — ContextSection/Priority |
| umh/context/budget.py | Live — token budget |
| umh/feedback/loop.py | Live — outcome recording |
| umh/adapters/llm.py | Live — LLM adapter discovery |
| umh/adapters/base.py | Live — adapter registry |
| umh/intent/compiler.py | Live — intent classification |
| umh/signal/ingest.py | Live — signal classification |
| umh/signal/types.py | Live — SignalBundle |
| umh/decision/trace.py | Live — DecisionTrace |
| umh/goals/ | Live — GoalState, GoalRegistry, interfaces |
| umh/strategy/ | Live — StrategyStats, interfaces |
| umh/world/ | Live — WorldModel, simulation, reasoning, calibration |
| umh/primitives/ | Live — ontological primitives |
| umh/goals/engine.py | Live — adaptive weight tuning (Wave 1) |
| umh/governance/capability.py | Live — permission + risk matrix (Wave 1) |
| umh/governance/governor.py | Live — controlled self-modification (Wave 1) |
| umh/execution/quality.py | Live — output quality gate (Wave 1) |
| umh/execution/harness.py | Live — multi-step agent orchestration (Wave 1) |
| umh/world/substrate.py | Live — entity/relation/state substrate (Wave 1) |
| umh/feedback/dynamics.py | Live — delayed/nonlinear feedback modeling (Wave 1) |
| umh/signal/event_bus.py | Live — reactive pub/sub coordination (Wave 1) |

Tests: 508 passing (baseline=18, boundaries=72, context=33, routing=48, llm_adapter=36, mvp=74, harness=33, goal_engine=41, capability=48, quality=12, substrate=12, dynamics=27, governor=26, event_bus=28)

---

## Collapse Log

### Wave 0 — Inventory (Phase 1)

_Completed: three parallel inventory agents scanned _holding, root symlinks, and docs/config/tooling. Results informed Wave 1 extraction priorities._

### Wave 1 — Extractions

| Timestamp | Action | Source | Target | Category | Tests Added | Notes |
|-----------|--------|--------|--------|----------|-------------|-------|
| 2026-04-24 | extract+purify | _holding/runtime_legacy/core/agent_harness.py | umh/execution/harness.py | UMH_CORE | 22 (test_umh_harness.py) | Protocol injection replaces 5 lazy imports; Option B integration via run_harness() |
| 2026-04-24 | extract+purify | _holding/runtime_legacy/eos_ai/goal_engine.py | umh/goals/engine.py | UMH_CORE | 41 (test_umh_goal_engine.py) | Direct copy, docstring fix, restore() hardened for bad data |
| 2026-04-24 | extract+purify | _holding/runtime_legacy/core/capability.py | umh/governance/capability.py | UMH_CORE | 42 (test_umh_capability.py) | Capability→CapabilityLevel, Decision→CapabilityDecision, hardcoded agents→ProfileRegistry archetypes |
| 2026-04-24 | extract+purify | _holding/runtime_legacy/eos_ai/quality_gate.py | umh/execution/quality.py | UMH_CORE | 12 (test_umh_quality.py) | Top-half only; SignalTier enum→string comparison; ctx made optional |
| 2026-04-24 | extract+purify | _holding/runtime_legacy/eos_ai/world_substrate.py | umh/world/substrate.py | UMH_CORE | 12 (test_umh_substrate.py) | Import changed from eos_ai.world_types→umh.world.types |
| 2026-04-24 | extract (verbatim) | _holding/runtime_legacy/core/dynamics.py | umh/feedback/dynamics.py | UMH_CORE | 27 (test_umh_dynamics.py) | Pure stdlib, zero changes needed; docstring updated |
| 2026-04-24 | extract+purify | _holding/runtime_legacy/core/improvement_governor.py | umh/governance/governor.py | UMH_CORE | 26 (test_umh_governor.py) | Hardcoded paths→constructor injection; removed singleton |
| 2026-04-24 | extract+purify | _holding/runtime_legacy/eos_ai/event_bus.py | umh/signal/event_bus.py | UMH_CORE | 23 (test_umh_event_bus.py) | Pattern only (bus+subscribe+publish); handlers are instance data; Neon persistence→EventLogger protocol |

### Wave 2 — Duplicate Collapse

| Timestamp | Duplicate | UMH Equivalent | Action | Notes |
|-----------|-----------|----------------|--------|-------|
| 2026-04-24 | core/dynamics.py (270 lines) | umh/feedback/dynamics.py | SHIMMED | Full replacement — identical exports |
| 2026-04-24 | core/improvement_governor.py (327 lines) | umh/governance/governor.py | SHIMMED | Re-exports + get_governor() compat with EOS paths |
| 2026-04-24 | core/capability.py (510 lines) | umh/governance/capability.py | SHIMMED | Name aliases: Capability→CapabilityLevel, Decision→CapabilityDecision; legacy profile names mapped |
| 2026-04-24 | eos_ai/goal_engine.py (540 lines) | umh/goals/engine.py | SHIMMED | Full replacement — all constants + classes re-exported |
| 2026-04-24 | eos_ai/quality_gate.py (525 lines) | umh/execution/quality.py | PARTIAL SHIM | Types from UMH; quality_check() + gate_outgoing_email() remain (EOS-coupled) |
| 2026-04-24 | eos_ai/world_substrate.py (379 lines) | umh/world/substrate.py | SHIMMED | Full replacement — Entity re-exported from umh.world.types |
| 2026-04-24 | core/agent_harness.py (740 lines) | umh/execution/harness.py | NO SHIM | Different API design — legacy uses lazy imports, UMH uses Protocol injection. Not interchangeable. |
| 2026-04-24 | eos_ai/event_bus.py (509 lines) | umh/signal/event_bus.py | NO SHIM | Legacy has singleton+Neon persistence+handler registry. UMH is clean pattern reimplementation. Different classes. |
| 2026-04-24 | core/capabilities.py (330 lines) | umh/capability/registry.py | NO SHIM | Different field names (strengths/weaknesses vs tags/metadata). Legacy consumers depend on exact fields. |
| 2026-04-24 | core/execution_contract.py (384 lines) | — | NOT A DUPLICATE | Legacy is EOS runtime entry point (run_task); UMH contract.py is type definitions. Different concerns. |
| 2026-04-24 | core/context.py (124 lines) | — | NOT A DUPLICATE | Legacy is L1 composition context (primitives); UMH context/ is LLM prompt assembly. Different concerns. |

#### Already shimmed (before Wave 2):
- core/objective_engine.py → umh/goals/objective.py
- core/primitives.py → umh/primitives/ontological.py
- eos_ai/execution_spine.py → umh compatibility shell
- eos_ai/decision_trace.py → umh/decision/trace.py
- eos_ai/goal_state.py → umh/goals/state.py
- eos_ai/strategy_memory.py → umh/strategy/memory.py
- eos_ai/world_model.py → umh/world/model.py
- eos_ai/world_state.py → umh/world/state.py
- eos_ai/world_types.py → umh/world/types.py
- eos_ai/world_calibration.py → umh/world/calibration.py
- eos_ai/world_dynamics_adapter.py → umh/world/dynamics_adapter.py
- eos_ai/world_reasoning.py → umh/world/reasoning.py
- eos_ai/world_simulation.py → umh/world/simulation.py
- eos_ai/substrate/execution_contract.py → umh/execution/contract.py
- eos_ai/stages/*.py (8 modules) → umh execution stages

### Wave 2B — Structural Convergence

_Completed: three non-shimmable modules merged into UMH via architecture convergence._

| Timestamp | Legacy Module | UMH Target | Action | Features Added to UMH | Consumer Rewrites Needed |
|-----------|---------------|------------|--------|----------------------|-------------------------|
| 2026-04-24 | core/agent_harness.py (740) | umh/execution/harness.py | REPLACED_NOT_SHIMMED | CapabilityGate Protocol, NoGate, EnforcerGate, risk field on HarnessTask, per-step permission gating, operation+provider on HarnessResult | persistent_agents, advisor, eos_os_smoke_test |
| 2026-04-24 | core/capabilities.py (330) | umh/capability/registry.py | REPLACED_NOT_SHIMMED | effective_quality() blending, cost_efficiency, PersistenceBackend Protocol, record_outcome(), weaknesses field, latency_score, supports_task() | router, matcher |
| 2026-04-24 | eos_ai/event_bus.py (509) | umh/signal/event_bus.py | REPLACED_NOT_SHIMMED | EventRegistry bulk handler wiring, add()+register_all() chaining, pending count | coordination_engine, gateway, reality_engine, calendly_webhook, dm_monitor, icp_scorer, telegram_control, substrate.station |

Also in this wave:
- Added OperationKind.READ_GRAPH to umh/governance/capability.py
- Updated operation_for_action_type() to route graph operations
- Tests: 33 harness (was 22) + 28 event_bus (was 23) + 48 capability (was 42) + routing convergence tests

### Wave 2C — Consumer Migration

_Completed: all live consumers migrated off REPLACED_NOT_SHIMMED legacy modules._

**Batch 1 — core.agent_harness consumers:**

| File | Change | Status |
|------|--------|--------|
| scripts/eos_os_smoke_test.py | `import core.agent_harness` → `from umh.execution.harness import AgentHarness`; check_harness() rewritten to UMH API (EnforcerGate, HarnessTask, run_harness) | DONE |

**Batch 2 — eos_ai.event_bus consumers:**

| File | Change | Status |
|------|--------|--------|
| eos_ai/event_bus.py (live) | Complete rewrite: imports from umh.signal.event_bus, NeonEventLogger (EventLogger protocol), get_bus() singleton, EOSEventRegistry(EventRegistry) | DONE |
| eos_ai/coordination_engine.py | `EventBus()` → `get_bus()` | DONE |
| eos_ai/reality_engine.py | `EventBus()` → `get_bus()` | DONE |
| eos_ai/gateway.py | `EventBus()` → `get_bus()`, `len(results)` → `result.handlers_called` | DONE |
| eos_ai/integration_test.py | `EventBus, EventRegistry` → `get_bus, EOSEventRegistry` | DONE |
| eos_ai/substrate/station.py | `EventBus()` → `get_bus()` (lazy import) | DONE |
| services/telegram_control.py | `EventBus()` → `get_bus()` (lazy import) | DONE |
| services/calendly_webhook.py | `EventBus()` → `get_bus()` (lazy import) | DONE |
| services/dm_monitor.py | `EventBus()` → `get_bus()` (lazy import) | DONE |
| services/icp_scorer.py | `EventBus()` → `get_bus()` (lazy import) | DONE |
| scripts/substrate_drainer_smoke_test.py | `EventBus()` → `get_bus()` | DONE |

**Batch 3 — core.capabilities consumers:**

Zero live consumers outside core/ — already clean. Remaining core/ internal imports
(core/router.py, core/matcher.py) are themselves in the NEEDS_REVIEW migration queue.

**Migration totals:**
- eos_ai.event_bus: 10/10 consumers migrated → **SAFE_TO_DELETE** (legacy _holding copy)
- core.agent_harness: 1/1 non-core consumer migrated; 3 core/ internal consumers remain (persistent_agents, advisor, agent_harness self-reference) — blocked on core/ module extraction
- core.capabilities: 0 non-core consumers; 3 core/ internal consumers remain (router, matcher, capabilities self-reference) — blocked on core/ module extraction

### Wave 3B — Core Internal Collapse

_Completed: core/ modules migrated off legacy capabilities/harness imports to UMH._

| File | Legacy Import | UMH Replacement | Changes |
|------|---------------|-----------------|---------|
| core/matcher.py | `core.capabilities` (Capability, list_capabilities, CAPABILITY_REGISTRY) | `umh.capability.registry` (Capability, get_registry) | Field renames: type→capability_type, cost→cost_per_call, latency→latency_score, supported_tasks→tags; list_capabilities→registry.by_type()/list_available(); CAPABILITY_REGISTRY→get_registry().list_all() |
| core/router.py | `core.capabilities` (Capability, record_outcome) | `umh.capability.registry` (Capability, get_registry) | Same field renames; record_outcome(latency_s=)→get_registry().record_outcome(latency_ms=) |
| core/advisor.py | `core.capability` (RiskTier, coerce_risk) | `umh.governance.capability` (direct) | Bypasses shim — imports directly from UMH |
| core/agent_harness.py | `core.capability` (CapabilityEnforcer, OperationKind, RiskTier, DEFAULT_PROFILES, get_profile, operation_for_action_type) | `umh.governance.capability` (direct) | Bypasses shim — builds EOS profiles from UMH ProfileRegistry; inlines get_profile() and _build_profiles() |
| core/persistent_agents.py | `core.agent_harness` (AgentHarness, default_harness) | No change (EOS integration harness) | Agent harness is EOS-specific integration layer, not a UMH duplicate — kept as-is with its imports now transiting directly to UMH |

**Remaining `core.capabilities` (plural) imports:** zero (self-reference only)
**Remaining `core.capability` (singular, shim) imports:** core/security/*, scripts/action_system.py, scripts/eos_os_smoke_test.py — outside Wave 3B scope, shim still needed

### Wave 3 — Safe Deletions & Review Queue

#### SAFE_DELETE — shimmed modules whose original code is now redundant
These files are now thin shims re-exporting from UMH. The original implementation
logic has been removed. No data loss on deletion — UMH is the canonical source.

| File | Lines removed | Replacement |
|------|--------------|-------------|
| core/dynamics.py | 270 → 22 | umh/feedback/dynamics.py |
| core/improvement_governor.py | 327 → 35 | umh/governance/governor.py |
| core/capability.py | 510 → 72 | umh/governance/capability.py |
| eos_ai/goal_engine.py | 540 → 27 | umh/goals/engine.py |
| eos_ai/world_substrate.py | 379 → 20 | umh/world/substrate.py |

Note: these files should NOT be deleted yet — they are shims providing backward
compatibility for legacy consumers. Delete only when all consumers are migrated.

#### NEEDS_REVIEW — duplicates that can't be cleanly shimmed

| File | Reason | Blocking issue | Status |
|------|--------|---------------|--------|
| core/agent_harness.py (740 lines) | UMH harness has different API | Legacy consumers use lazy-import coupling | **RESOLVED (Wave 2B)** — REPLACED_NOT_SHIMMED |
| core/capabilities.py (330 lines) | Different data model | Legacy fields differ from UMH | **RESOLVED (Wave 2B)** — REPLACED_NOT_SHIMMED |
| eos_ai/event_bus.py (509 lines) | Singleton + Neon persistence | UMH is Protocol-based | **RESOLVED (Wave 2B)** — REPLACED_NOT_SHIMMED |
| eos_ai/quality_gate.py (partial) | EOS-coupled functions remain | quality_check() and gate_outgoing_email() use model_router + db | Open |

#### Remaining legacy modules (NOT duplicates — unique functionality)

| File | Lines | Category | Notes |
|------|-------|----------|-------|
| core/self_improvement.py | 481 | NEEDS_REVIEW | Needs transformer extraction first |
| core/memory_evolution.py | 557 | NEEDS_REVIEW | Needs primitives+transformer |
| core/advisor.py | 863 | NEEDS_REVIEW | Large; uses harness+capability |
| core/environment.py | 534 | INSTANCE_DATA | Hardcoded EOS paths |
| core/optimizer.py | 651 | INSTANCE_DATA | EOS-specific log heuristics |
| core/execution_bridge.py | 1313 | NEEDS_REVIEW | Large integration layer |
| core/persistent_agents.py | 565 | NEEDS_REVIEW | Uses agent_harness |
| core/transformer.py | 337 | NEEDS_REVIEW | Would unlock self_improvement + memory_evolution |
| core/composer.py | 319 | NEEDS_REVIEW | Uses context + primitives |
| core/router.py | 316 | NEEDS_REVIEW | Uses capabilities (legacy) |
| core/matcher.py | 330 | NEEDS_REVIEW | Uses capabilities (legacy) |
| core/observability.py | 407 | INSTANCE_DATA | Reads EOS log files |
| core/control_plane.py | 321 | NEEDS_REVIEW | May overlap umh/governance |
| core/reality_input.py | 328 | NEEDS_REVIEW | Signal processing |
| core/semantic_space.py | 506 | NEEDS_REVIEW | Requires numpy |

---

## Wave 3C — Final Shim Collapse + Cleanup (2026-04-24)

**Goal:** Remove all remaining legacy capability shims; UMH is sole source of truth.

### Migrations performed

| File | Old import | New import | Notes |
|------|-----------|------------|-------|
| core/security/context.py | core.capability | umh.governance.capability | OperationKind, RiskTier, coerce_risk |
| core/security/environments.py | core.capability | umh.governance.capability | RiskTier, coerce_risk |
| core/security/rbac.py | core.capability | umh.governance.capability | CapabilityLevel as Capability, OperationKind, RiskTier + helpers |
| scripts/action_system.py | core.capability | umh.governance.capability | OperationKind, operation_for_action_type |
| scripts/eos_os_smoke_test.py | core.capability | umh.governance.capability | Full rewrite of check_capability() |

### Enum fixes

| Old name | New name | Files affected |
|----------|----------|---------------|
| OperationKind.EDIT_CRITICAL_HUB | OperationKind.EDIT_CRITICAL | rbac.py (2), eos_os_smoke_test.py (2) |

### Docstring updates

| File | Reference changed |
|------|-------------------|
| core/advisor.py:29 | core.capability → umh.governance.capability |
| core/agent_harness.py:22 | core.capability.CapabilityEnforcer → umh.governance.capability |
| core/agent_harness.py:54 | core.capability → umh.governance.capability |
| core/security/rbac.py:2,6,187 | core.capability → umh.governance.capability |

### Files deleted

| File | Lines | Reason |
|------|-------|--------|
| core/capability.py | 62 | Shim — zero consumers remain |
| core/capabilities.py | 330 | Legacy registry — zero external consumers |

### Verification

- All 5 migrated files compile and import cleanly
- RBAC engine: 4 role checks pass (admin/viewer/operator/agent)
- Security environments: prod/dev policy checks pass
- Smoke test capability check: reader/executor assertions pass
- 120 UMH tests pass (capability + event_bus + governor + baseline)
- Zero remaining `core.capability` or `core.capabilities` imports in live code

### Totals after Wave 3C

| Metric | Count |
|--------|-------|
| Files migrated (Waves 2C+3B+3C) | 21 |
| Legacy shims deleted | 2 |
| Remaining core.capability imports | 0 |
| Remaining core.capabilities imports | 0 |

---

### Wave 4 — Infrastructure Extraction (2026-04-24)

**Goal:** Extract context, DB, and business instance infrastructure into UMH.
Establish interface contracts for Discord/Telegram transports.

#### UMH modules created

| File | Lines | Source | Category | Notes |
|------|-------|--------|----------|-------|
| umh/environments/system_context.py | ~80 | eos_ai/context.py | UMH_CORE | SystemContext dataclass + load_context_from_env(); optional dotenv; EOSContext alias |
| umh/storage/adapters/__init__.py | ~5 | (new) | UMH_CORE | Package init |
| umh/storage/adapters/neon.py | ~148 | eos_ai/db.py | UMH_CORE | Lazy init via _ensure_dotenv(); get_conn() with RLS; resolve_venture/skill helpers |
| umh/workstation/business.py | ~350 | eos_ai/business_instance.py | UMH_CORE | BusinessInstance dataclass (~40 fields); BusinessInstanceManager; STAGE_NAMES/PROOF_GATES/GUIDANCE; get_ai_name() |
| umh/interface/discord/__init__.py | ~10 | (new) | UMH_INTERFACE_PROTOTYPE | Transport contract documentation |
| umh/interface/telegram/__init__.py | ~10 | (new) | UMH_INTERFACE_PROTOTYPE | Transport contract documentation |
| external_services/__init__.py | ~15 | (new) | NON_UMH_PRODUCT_OR_NOISE | Classification of outreach/monitoring services |

#### Compatibility wrappers modified

| File | Action | Notes |
|------|--------|-------|
| eos_ai/context.py | SHIMMED | Re-exports EOSContext, SystemContext, load_context_from_env from umh.environments.system_context |
| eos_ai/db.py | SHIMMED | Delegates get_conn/resolve_venture/resolve_skill to UMH; keeps ORG_ID/USER_ID read locally (Python binding semantics — scalar re-export is stale after reassignment) |
| eos_ai/business_instance.py | SHIMMED | Full re-export from umh.workstation.business |

#### Transitional eos_ai imports in UMH (ALLOWED_EOS_IMPORTS)

| UMH File | Import | Reason | Removal Target |
|----------|--------|--------|----------------|
| umh/workstation/business.py | eos_ai.agent_runtime | Lazy: create_from_wizard needs AgentRuntime for AI-assisted wizard | Phase 6 |
| umh/workstation/business.py | eos_ai.execution_spine | Lazy: create_from_wizard uses SpineResult for LLM responses | Phase 6 |
| umh/workstation/business.py | eos_ai.context_builder | Lazy: create_from_wizard needs context assembly for prompts | Phase 6 |

#### Tests added

- tests/unit/test_umh_wave4_extraction.py — 23 tests (system_context, neon adapter, business_instance, compatibility wrappers, interface packages)
- tests/unit/test_umh_boundaries.py — updated ALLOWED_EOS_IMPORTS with 3 entries for umh/workstation/business.py
- tests/unit/test_umh_wave0_standalone.py — updated to respect ALLOWED_EOS_IMPORTS (prevents false positives from transitional imports)

---

### Wave 5 — Routing / Model Runtime Collapse (2026-04-24)

**Goal:** Extract the generic multi-provider model routing engine from eos_ai/model_router.py into UMH.
Keep EOS-specific glue (Claude CLI tmux, CC SDK, Discord mode routing, execution trace stamping, CEO agent keywords) in the eos_ai compatibility wrapper.

#### Decision: agent_runtime.py NOT extracted

eos_ai/agent_runtime.py is almost entirely EOS-platform-specific (LLM dispatch, fallback chain, Claude availability detection). The only generic parts — TaskType (6 members, already a subset of UMH's 20-member TaskType), RateLimiter, calculate_cost() — are too small or coupled to justify extraction. Left as-is.

#### UMH module created

| File | Lines | Source | Category | Notes |
|------|-------|--------|----------|-------|
| umh/adapters/model_router.py | ~560 | eos_ai/model_router.py | UMH_CORE | Generic multi-provider routing engine; zero eos_ai imports |

**Public API exported:**

| Symbol | Type | Description |
|--------|------|-------------|
| ModelProvider | Enum (9) | claude_cli, cc_sdk, anthropic, perplexity, openai, groq, ollama, gemini, manus |
| TaskType | Enum (20) | conversation, analysis, web_search, market_intel, fast_response, long_context, autonomous, multimodal, browser_control, score, classify, analyze, generate, summarize, strategic, code, research, self_improve, plan, coordinate |
| ModelConfig | dataclass | provider, model_id, api_key_env, strengths, cost_per_1k, available, base_url |
| RoutingResult | dataclass | output, provider, model, task_type, tokens_used, input_tokens, output_tokens, cost_estimate, latency_ms |
| ModelRouter | class | route(), call(), call_with_fallback(), check_availability(), get_status() |
| CC_MODEL_MAP | dict | task_type → Claude model mapping |
| PROVIDER_PRIORITY | dict | ModelProvider → int (heavy path) |
| PROVIDER_PRIORITY_FAST | dict | ModelProvider → int (fast path) |
| FAST_TASK_TYPES | set | Task types routed through fast/cheap providers |
| HAIKU_TOKEN_CAPS | dict | task_type → max tokens for Haiku |
| PROVIDER_QUALITY | dict | provider → baseline quality score |
| ESCALATION_QUALITY_THRESHOLD | float | 0.40 — below this, escalate to stronger model |
| TASK_TYPE_MAP | dict | Maps extended task type names to router strength categories |
| build_default_registry() | function | Returns 7 default ModelConfig entries |
| estimate_quality_score() | function | Heuristic 0.0–1.0 quality scoring |
| should_escalate() | function | Returns True if quality too low |
| ollama_available() | function | HTTP health check |
| call_anthropic() | function | Direct Anthropic API call → (output, in_tok, out_tok) |
| call_openai_compatible() | function | OpenAI-compatible API call → (output, in_tok, out_tok) |
| call_ollama() | function | Ollama API call → (output, in_tok, out_tok) |
| call_gemini() | function | Gemini API call → (output, in_tok, out_tok) |
| get_router() | function | Module-level singleton getter |
| reset_router() | function | Clears singleton for testing |

#### Compatibility wrapper modified

| File | Action | Notes |
|------|--------|-------|
| eos_ai/model_router.py | SHIMMED (~415 lines) | Re-exports all generic types from UMH; adds Claude CLI tmux backend (#0), CC SDK escalation, Discord mode routing, trace stamping, CEO agent keywords, adversarial_code_review stub |

**EOS-specific functionality kept in wrapper:**

| Feature | Why not in UMH |
|---------|----------------|
| Claude CLI tmux backend | EOS deployment-specific (tmux session management) |
| CC SDK integration | eos_ai.cc_sdk is EOS-coupled |
| Discord mode routing | eos_ai.substrate.discord_mode_routing |
| Execution trace stamping | eos_ai.substrate.execution_trace |
| CEO agent keyword detection | EOS org-chart concept |
| adversarial_code_review() stub | EOS Codex integration point |

#### Bugs fixed during extraction

| Bug | Root cause | Fix |
|-----|-----------|-----|
| `ModelRouter(registry={})` uses default registry | `{}` is falsy in Python, so `registry or build_default_registry()` always defaults | Changed to `registry if registry is not None else build_default_registry()` |
| OpenAI missing from priority tables | ModelProvider.OPENAI in enum but not in PROVIDER_PRIORITY/PROVIDER_PRIORITY_FAST | Added at priority 5 (default) and 4 (fast) |
| Wave 0 test_no_from_eos_ai_import fails | umh/workstation/business.py has 3 documented transitional eos_ai imports | Updated test to import and respect ALLOWED_EOS_IMPORTS from test_umh_boundaries.py |

#### Direct model/LLM call sites still remaining (bypass model_router)

| File | Call type | Notes |
|------|-----------|-------|
| eos_ai/agent_runtime.py | anthropic.Anthropic() + google.genai | Has own fallback chain; uses model_router.TaskType |
| eos_ai/cc_sdk.py | Claude Code SDK subprocess | CC SDK is itself a provider, not a consumer |
| eos_ai/substrate/claude_responder.py | tmux send-keys | Substrate-level, not model routing |
| services/telegram_control.py | Lazy model_router import | Goes through call_with_fallback — correct path |

#### Tests added

- tests/unit/test_umh_wave5_model_routing.py — 28 tests across 8 classes:
  - TestUMHModelRouterStandalone (4): imports, no eos_ai in source, TaskType enum completeness, ModelProvider enum completeness
  - TestModelRouterCore (5): build_default_registry, route empty, route available, fallback exhaustion, RoutingResult, get_status
  - TestQualityEstimation (5): empty output, short output, refusal pattern, normal output, escalation triggers
  - TestSingleton (2): get_router identity, reset_router clears
  - TestCCModelMap (3): covers all task types, strategic→opus, fast→haiku
  - TestLegacyCompatibility (4): legacy import path, type identity, agent_runtime import, adversarial_code_review
  - TestProviderPriority (3): default priority has all providers, fast priority has all providers, fast task types defined

#### Verification

- 28 Wave 5 tests: all pass
- Wave 0 standalone tests: pass (including ALLOWED_EOS_IMPORTS compliance)
- `python3 -m py_compile umh/adapters/model_router.py`: clean
- `python3 -m py_compile eos_ai/model_router.py`: clean
- `from umh.adapters.model_router import ModelRouter, TaskType, get_router`: works standalone
- `from eos_ai.model_router import call_with_fallback, TaskType, get_router`: backward compat works
- Legacy type identity: `eos_ai.model_router.TaskType is umh.adapters.model_router.TaskType` → True

#### Totals after Wave 5

| Metric | Count |
|--------|-------|
| UMH modules (new this wave) | 1 |
| Compatibility wrappers (modified this wave) | 1 |
| Public API symbols preserved | 22 |
| EOS-specific features kept in wrapper | 6 |
| Direct model call bypasses remaining | 4 |
| Tests added | 28 |
| Transitional eos_ai imports in UMH | 3 (from Wave 4, unchanged) |

---

### Wave 6 — Execution Runtime Collapse (2026-04-24)

**Goal:** Extract generic execution runtime mechanics (rate limiting, cost calculation,
result envelope, call lifecycle, observer hooks) from eos_ai/agent_runtime.py into UMH.
Turn eos_ai/agent_runtime.py into a compatibility/policy wrapper.

#### Decision: execution_spine.py NOT modified

eos_ai/execution_spine.py already delegates through UMH execution engine via `run_via_umh()`.
SpineResult (str subclass) and the 9-stage pipeline are EOS-specific. No generic mechanics
to extract. Left as-is — already a thin shell.

#### UMH module created

| File | Lines | Source | Category | Notes |
|------|-------|--------|----------|-------|
| umh/execution/runtime.py | ~240 | eos_ai/agent_runtime.py | UMH_CORE | Generic execution runtime; zero eos_ai imports |

**Public API exported:**

| Symbol | Type | Description |
|--------|------|-------------|
| RuntimeResult | dataclass | ok/output/error result envelope with cost, tokens, timing metadata |
| RateLimiter | class | In-memory per-org rate limiting (per-minute + per-hour) with reset() |
| calculate_cost() | function | USD cost from model + token counts |
| COST_PER_MILLION_TOKENS | dict | 7 models: Haiku, Sonnet, Opus, Gemini, Llama, Sonar, Qwen |
| DEFAULT_COST_RATES | dict | Fallback rates for unknown models |
| execute_with_fallback() | function | Full lifecycle: rate limit → UMH model router → cost → RuntimeResult |
| RuntimeObserver | Protocol | on_call_start, on_call_complete, on_rate_limited, on_retry |
| NullRuntimeObserver | class | No-op default observer |
| set_runtime_observer() | function | Inject observer for monitoring |
| get_runtime_observer() | function | Get current observer |
| MAX_RETRIES | int | 4 |
| BACKOFF_BASE | int | 2 seconds |

#### Compatibility wrapper modified

| File | Action | Notes |
|------|--------|-------|
| eos_ai/agent_runtime.py | SHIMMED (~310 lines) | Re-exports RateLimiter, calculate_cost, COST_PER_MILLION_TOKENS from UMH; keeps AgentRuntime class with all EOS orchestration |

**EOS-specific functionality kept in wrapper:**

| Feature | Why not in UMH |
|---------|----------------|
| AgentRuntime class | Orchestrates soul docs, venture context, skill injection, memory, authority |
| AgentResult dataclass | EOS-specific fields (skill_used, authority, interaction_id for Neon persistence) |
| TaskType enum (6 members) | EOS subset; UMH has 20-member superset in model_router |
| Soul doc loading | agent_hierarchy + BIS + file system paths |
| Venture context injection | VentureKnowledgeBase.to_agent_context() |
| Skill registry + auto-selection | get_skill_registry(), get_relevant_skills() |
| Semantic memory retrieval | AgentMemory.semantic_search() + outcome lookup |
| Human profile injection | HumanIntelligenceEngine for outreach tasks |
| Authority engine check | AuthorityEngine.check_can_execute() |
| Model preference resolution | ModelPreferences with business context |
| run_team_task() | EOS agent teams routing |
| run_with_auto_skill() | EOS auto-skill selection |
| Deprecated .client property | Direct anthropic.Anthropic() — logged as deprecated |

#### Generic mechanics extracted

| Mechanic | Was in | Now in |
|----------|--------|--------|
| RateLimiter (per-org, per-minute/hour) | eos_ai/agent_runtime.py | umh/execution/runtime.py |
| calculate_cost() | eos_ai/agent_runtime.py | umh/execution/runtime.py |
| COST_PER_MILLION_TOKENS | eos_ai/agent_runtime.py | umh/execution/runtime.py (expanded from 3 to 7 models) |
| RuntimeResult envelope | (new) | umh/execution/runtime.py |
| execute_with_fallback() lifecycle | (new — generic path) | umh/execution/runtime.py |
| RuntimeObserver protocol | (new) | umh/execution/runtime.py |

#### Direct execution/model bypasses remaining

| File | Bypass type | Notes |
|------|------------|-------|
| eos_ai/agent_runtime.py:client property | anthropic.Anthropic() | Deprecated, logs warning |
| eos_ai/cc_sdk.py | Claude Code subprocess | Provider itself, not bypass |
| eos_ai/substrate/claude_responder.py | tmux send-keys | Substrate-level |

#### Tests added

- tests/unit/test_umh_wave6_execution_runtime.py — 28 tests across 9 classes:
  - TestUMHRuntimeStandalone (3): imports, no eos_ai in source, uses umh model_router
  - TestRuntimeResult (2): ok result, failed result
  - TestCostCalculation (4): known model, unknown model, zero tokens, cost table coverage
  - TestRateLimiter (4): first call, minute limit, org independence, reset
  - TestExecuteWithFallback (3): rate limited, returns RuntimeResult, never raises
  - TestObserverProtocol (3): null observer, set/get, custom observer events
  - TestLegacyAgentRuntimeCompat (5): public API, TaskType values, RateLimiter identity, calculate_cost identity, AgentResult fields
  - TestExecutionSpineCompat (3): imports, str subclass, repr
  - TestNoNewForbiddenImports (1): full UMH scan for eos_ai imports

#### Verification

- 28 Wave 6 tests: all pass
- Wave 0 standalone tests: pass
- Wave 5 model routing tests: pass (47 total with Wave 0)
- Boundary + Wave 4 tests: pass (95 total)
- `python3 -m py_compile umh/execution/runtime.py`: clean
- `python3 -m py_compile eos_ai/agent_runtime.py`: clean
- `python3 -m py_compile eos_ai/execution_spine.py`: clean
- `from umh.execution.runtime import *`: works standalone
- `from eos_ai.agent_runtime import AgentRuntime, TaskType, RateLimiter, calculate_cost`: backward compat works
- Identity: `eos_ai.agent_runtime.RateLimiter is umh.execution.runtime.RateLimiter` → True
- Identity: `eos_ai.agent_runtime.calculate_cost is umh.execution.runtime.calculate_cost` → True

#### Totals after Wave 6

| Metric | Count |
|--------|-------|
| UMH modules (new this wave) | 1 |
| Compatibility wrappers (modified this wave) | 1 |
| Public API symbols preserved (agent_runtime) | 7 (AgentRuntime, TaskType, AgentResult, RateLimiter, calculate_cost, COST_PER_MILLION_TOKENS, HAIKU/SONNET) |
| Generic mechanics extracted to UMH | 6 (RateLimiter, calculate_cost, COST_PER_MILLION_TOKENS, RuntimeResult, execute_with_fallback, RuntimeObserver) |
| EOS-specific features kept in wrapper | 12 |
| Direct execution bypasses remaining | 3 |
| Tests added | 28 |
| Transitional eos_ai imports in UMH | 3 (unchanged from Wave 4) |

---

### Wave 7 — Gateway Collapse (2026-04-24)

**Goal**: Eliminate all competing control planes in the gateway/service layer.
Make UMH the ONLY interpreter of signals, router of intent, and execution
entry point. Every LLM call from external services must flow through UMH.

**Strategy**: Do NOT rewrite the 1835-line gateway. Instead:
1. Define a canonical entry contract (UMHInput/UMHOutput)
2. Fix all direct LLM bypasses to route through UMH
3. Leave EOS business policy (approval gates, CEO context, etc.) in the wrapper

#### New UMH modules

| Module | Purpose |
|--------|---------|
| umh/gateway/__init__.py | Package exports: UMHInput, UMHOutput, translate_and_run, utility_llm_call |
| umh/gateway/entry.py | Canonical entry contract + utility LLM call routing |

#### Canonical entry contract

```python
@dataclass
class UMHInput:
    source: str           # discord, telegram, webhook, cli
    raw_input: str        # text / payload
    metadata: dict        # user_id, channel_id, timestamps
    attachments: list     # optional file/image payloads
    authority: AuthorityLevel
    org_id: str
    constraints: dict

@dataclass
class UMHOutput:
    success: bool
    response: str
    run_id: str
    operation: str
    capability_used: str
    metadata: dict
```

- `translate_and_run(UMHInput) → UMHOutput` — full 9-stage run loop
- `utility_llm_call(prompt, system, operation) → str` — lightweight LLM call via `dispatch_prompt()`

#### LLM bypasses eliminated

| File | Bypass | Was calling | Now calls |
|------|--------|-------------|-----------|
| eos_ai/gateway.py:classify_intent() | Intent classification | eos_ai.model_router.call_with_fallback | umh.gateway.entry.utility_llm_call |
| eos_ai/gateway.py:_web_search() | Web search | eos_ai.model_router.get_router().call_with_fallback | umh.gateway.entry.utility_llm_call |
| eos_ai/gateway.py:_handle_email_instruction() | Email extraction | eos_ai.model_router.get_router().call_with_fallback | umh.gateway.entry.utility_llm_call |
| services/handlers/intent_handler.py:run_gateway() | Cloning loop check | eos_ai.model_router.call_with_fallback | umh.gateway.entry.utility_llm_call |
| services/discord_bot.py:cmd_nurture() | Nurture draft | eos_ai.model_router.get_router().call | umh.gateway.entry.utility_llm_call |
| services/calendly_webhook.py | Cancellation recovery | eos_ai.model_router.get_router().call | umh.gateway.entry.utility_llm_call |
| services/dm_monitor.py | DM reply draft | eos_ai.model_router.call_with_fallback | umh.gateway.entry.utility_llm_call |
| services/handlers/cc_command_handler.py:handle_followup() | Follow-up draft | eos_ai.model_router.get_router().call | umh.gateway.entry.utility_llm_call |
| services/handlers/cc_command_handler.py:handle_block_day() | Date parsing | eos_ai.model_router.get_router().call | umh.gateway.entry.utility_llm_call |
| services/handlers/cc_command_handler.py:handle_cal() | Calendar extraction | eos_ai.model_router.call_with_fallback | umh.gateway.entry.utility_llm_call |

#### Remaining model_router references

| Location | Status | Notes |
|----------|--------|-------|
| eos_ai/ domain modules (~60 call sites) | Legitimate | Invoked through gateway → ExecutionSpine → run_via_umh. Wave 8+ scope |
| services/discord_bot.py (2 comments) | Comment only | Not call sites |
| services/handlers/intent_handler.py (2 comments) | Comment only | Not call sites |

#### Execution path verification

All external signals now flow through UMH:

```
Discord/Telegram/Webhook
  → eos_ai/gateway.py (EOS policy wrapper)
    → SessionRuntime → ExecutionSpine → run_via_umh()
      → umh.execution.engine.execute()  ✓

Utility LLM calls (classify, search, extract)
  → umh.gateway.entry.utility_llm_call()
    → umh.execution.engine.dispatch_prompt()
      → umh.adapters.base.get_adapter("llm")  ✓
```

#### Tests added

- tests/unit/test_umh_wave7_gateway_collapse.py — 26 tests across 9 classes:
  - TestUMHGatewayStandalone (4): imports, no eos_ai in source, uses dispatch, exports
  - TestUMHInput (4): minimal construction, full construction, required fields, optional defaults
  - TestUMHOutput (2): from_run_result, error factory
  - TestUtilityLLMCall (3): callable, signature, uses dispatch_prompt
  - TestGatewayBypassesEliminated (4): no model_router imports, classify uses UMH, web_search uses UMH, email uses UMH
  - TestServiceBypassesEliminated (5): intent_handler, cc_command_handler, calendly, dm_monitor, discord_bot
  - TestTranslateAndRun (3): callable, returns UMHOutput, error returns UMHOutput
  - TestNoNewEosImportsInUMH (1): full UMH scan

#### Verification

- 26 Wave 7 tests: all pass
- Wave 0 standalone tests: 19 pass
- `python3 -m py_compile` on all modified files: clean
- Full UMH boundary scan: clean (3 pre-existing transitional imports in workstation/, documented)
- Gateway model_router imports: zero
- Services model_router call-site imports: zero

#### Totals after Wave 7

| Metric | Count |
|--------|-------|
| UMH modules (new this wave) | 2 (gateway/__init__.py, gateway/entry.py) |
| Files modified (bypasses fixed) | 7 (gateway.py, intent_handler.py, discord_bot.py, calendly_webhook.py, dm_monitor.py, cc_command_handler.py, test_umh_wave0_standalone.py) |
| LLM bypasses eliminated | 10 |
| Direct model_router call sites remaining in services/ | 0 |
| EOS domain modules with model_router calls (future waves) | ~60 |
| Tests added | 26 |
| Transitional eos_ai imports in UMH | 3 (unchanged from Wave 4) |

---

### Wave 8 — Context Assembly Collapse (2026-04-24)

**Goal**: Unify all context building and lightweight LLM usage into UMH.
Eliminate the parallel "utility" path. After this, there is ONE way to
build prompts, call LLMs, and assemble context.

**Strategy**: The EOS context_builder.py is 100% platform-specific (20+
data sources: AI identity, EA standards, BIS, founder profile, brand,
primitives, hierarchy, calendar, memory, etc.). The generic ContextBuilder
pattern already lives in UMH. The fix is to ensure the lightweight utility
path routes through the same execution engine as the full run loop.

#### What changed

| Component | Before | After |
|-----------|--------|-------|
| utility_llm_call | dispatch_prompt() → adapter directly | lightweight_execute() → execute() → backend |
| Lightweight context | No context assembly | ContextBuilder with sections |
| Task types | Implicit string | LightweightTaskType enum (5 members) |
| Execution pipeline | Two paths (execute + dispatch_prompt) | One engine, two entry points |

#### New in UMH

| Addition | Location | Purpose |
|----------|----------|---------|
| LightweightTaskType enum | umh/execution/engine.py | Canonical task types: classify_intent, extract_entities, summarize, short_response, validation |
| lightweight_execute() | umh/execution/engine.py | Builds ExecutionRequest internally, routes through execute() |

#### Architecture after Wave 8

```
Full run loop (umh.run):
  Signal → Intent → World → Decision → Route → Compose → Govern → Execute
    ↓
  execute(ExecutionRequest) → Backend → Observer
    ↓
  dispatch_prompt() → adapter registry → LLM

Lightweight path (utility_llm_call):
  utility_llm_call()
    → lightweight_execute()
      → ContextBuilder (4K token budget, system + task sections)
      → ExecutionRequest (LLM_CALL class)
      → execute() → Backend → Observer
                       ↓
                  Same pipeline as full runs
```

Both paths converge at execute() — one engine, one observer pipeline,
one backend.

#### What was NOT changed (and why)

| File | Why kept | Notes |
|------|----------|-------|
| eos_ai/context_builder.py | 100% EOS platform-specific | 20+ data sources. Generic patterns already in UMH. |
| dispatch_prompt() | Still used by umh/run.py Stage 8 | Run loop's internal adapter dispatch. Not exposed outside engine. |
| Inline prompt construction in services | Domain-specific content | Prompts are domain logic, not generic. Routing is through UMH. |

#### Tests added/updated

- tests/unit/test_umh_wave8_context_collapse.py — 24 tests across 9 classes
- Updated 2 Wave 7 tests for new architecture

#### Verification

- 24 Wave 8 tests: all pass
- 19 Wave 0 standalone tests: pass (no regression)
- 26 Wave 7 gateway tests: pass (2 updated)
- Full UMH boundary scan: clean

#### Totals after Wave 8

| Metric | Count |
|--------|-------|
| UMH modules modified | 2 (execution/engine.py, gateway/entry.py) |
| New execution entry points | 1 (lightweight_execute) |
| New task type enums | 5 (LightweightTaskType members) |
| Execution paths through engine | 2, converging at execute() |
| Direct adapter calls from gateway | 0 |
| Tests added | 24 |
| Tests updated | 2 (Wave 7) |
| Transitional eos_ai imports in UMH | 3 (unchanged from Wave 4) |

---

### Wave 9: Wrapper Deletion (2026-04-25)

**Goal:** Delete ALL eos_ai pure compatibility wrappers. Make UMH the only import target.

#### What changed

| Action | Files | Details |
|--------|-------|---------|
| **REWIRED** | ~500 import sites | All `from eos_ai.X import` → `from umh.Y import` across repo |
| **DELETED** | 14 pure wrapper files | context.py, db.py, business_instance.py, goal_engine.py, goal_state.py, strategy_memory.py, world_calibration.py, world_dynamics_adapter.py, world_model.py, world_reasoning.py, world_simulation.py, world_state.py, world_substrate.py, world_types.py |
| **RETAINED** | 7 WRAPPER+GLUE files | model_router.py, agent_runtime.py, quality_gate.py, decision_trace.py, event_bus.py, execution_spine.py, cognitive_loop.py |

#### Import rewiring map

| Old import | New import |
|------------|-----------|
| `eos_ai.context` | `umh.environments.system_context` |
| `eos_ai.db` | `umh.storage.adapters.neon` |
| `eos_ai.business_instance` | `umh.workstation.business` |
| `eos_ai.goal_engine` | `umh.goals.engine` |
| `eos_ai.goal_state` | `umh.goals.state` |
| `eos_ai.strategy_memory` | `umh.strategy.memory` |
| `eos_ai.world_calibration` | `umh.world.calibration` |
| `eos_ai.world_dynamics_adapter` | `umh.world.dynamics_adapter` |
| `eos_ai.world_model` | `umh.world.model` |
| `eos_ai.world_reasoning` | `umh.world.reasoning` |
| `eos_ai.world_simulation` | `umh.world.simulation` |
| `eos_ai.world_state` | `umh.world.state` |
| `eos_ai.world_substrate` | `umh.world.substrate` |
| `eos_ai.world_types` | `umh.world.types` |

#### Why retained files stay

| File | Reason |
|------|--------|
| `model_router.py` | Claude CLI tmux backend, CC SDK escalation, CEO detection, Discord mode routing, execution trace stamping |
| `agent_runtime.py` | Full AgentRuntime class: soul docs, venture context, skill registry, memory, authority checks |
| `quality_gate.py` | EOS-specific quality_check() and gate_outgoing_email() with Neon logging |
| `decision_trace.py` | build_trace() factory depends on EOS strategy_memory singleton |
| `event_bus.py` | NeonEventLogger, EOS event constants, EOSEventRegistry |
| `execution_spine.py` | SpineResult contract, 9-stage pipeline composition, run_via_umh() |
| `cognitive_loop.py` | DEPRECATED — format_response_footer still in use |

#### Tests

| Suite | Count | Result |
|-------|-------|--------|
| Wave 9 (test_umh_wave9_wrapper_removal.py) | 58 | PASS |
| Wave 8 (context collapse) | 24 | PASS |
| Wave 7 (gateway collapse) | 26 | PASS |
| UMH boundaries | 72 | PASS |
| UMH baseline | 18 | PASS |
| Domain tests (goal_engine, goal_state, world_*) | 493+ | PASS |

#### Verification

- 14 pure wrapper files deleted, zero importers remaining
- ~500 import sites rewired to UMH modules
- All UMH modules importable and functional
- No new eos_ai imports leaked into UMH
- No new compatibility wrapper patterns appeared
- 7 WRAPPER+GLUE files retained with EOS-specific business logic
- _holding/ directory imports NOT rewired (frozen archive)

#### Totals after Wave 9

| Metric | Count |
|--------|-------|
| Pure wrappers deleted | 14 |
| Import sites rewired | ~500 |
| WRAPPER+GLUE files retained | 7 |
| Wave 9 tests added | 58 |
| Total test count (Waves 0-9) | 278+ |
| eos_ai files remaining | ~160+ (domain logic + glue) |
| Transitional eos_ai imports in UMH | 3 (unchanged) |
