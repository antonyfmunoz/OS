# Phase 5B Revised: Whole-Repository Alignment Plan

**Date:** 2026-04-24
**Status:** Corrected plan — supersedes umh/ARCHITECTURE_ALIGNMENT.md
**Scope:** Entire /opt/OS repository → product-grade UMH repo

---

## Executive Summary

The previous Phase 5B report (umh/ARCHITECTURE_ALIGNMENT.md) correctly identified
UMH internal structure and contamination, but made four significant errors:

1. **Collapsed memory/ into storage/** — memory is an intelligence subsystem
   (semantic recall, episodic retrieval, working memory), storage/ is raw
   key-value persistence infrastructure. They are categorically different.
2. **Collapsed security/ into governance/** — governance is policy/authority
   decisions, security is access control/confidentiality/threat boundaries.
3. **Skipped environments/ and workstation/** — declared them empty-for-now.
   These are core UMH product subsystems that must exist as structural
   placeholders even if initially minimal.
4. **Scoped only umh/** — did not address the 467-file eos_ai legacy,
   _holding taxonomy, services, tools, infra, docs, tests, vault, logs,
   or Claude Code project files.

This revised plan covers the entire repository, preserves the correct parts
of the original report, and corrects the four errors above.

---

## 1. Current State

### File counts

| Location | Python files | Total files | Notes |
|---|---|---|---|
| `umh/` | 55 | 55 | 13,131 lines. The canonical UMH package. |
| `_holding/runtime_legacy/eos_ai/` | 467 | 467+ | ~207 top-level + ~197 substrate + 21 adapters + tests/stages/runtime/platforms |
| `_holding/runtime_legacy/services/` | 18 | 18 | Discord bot, telegram, webhooks, scrapers |
| `_holding/runtime_legacy/tests/` | ~170 | ~170 | Legacy + UMH tests (symlinked to /opt/OS/tests) |
| `_holding/runtime_legacy/scripts/` | ~20 | ~20 | Graph tools, ops scripts, cron jobs |
| `_holding/runtime_legacy/core/` | ~30 | ~30 | Action system, connectors, domain, orchestrator, security, tool mastery |
| `_holding/runtime_legacy/parsers/` | ~5 | ~5 | Input parsers |
| `_holding/claude_code_harnessing/` | 0 | ~100+ | Skills, agents, templates for Claude Code |
| `_holding/eos_product/` | 1 | ~25 | Agent soul docs, orchestrator dailies, SaaS bridge, ventures, products |
| `_holding/knowledge_vault/` | 0 | ~200+ | Obsidian vault, wiki, offers, workflows, content |
| `_holding/data_artifacts/` | 0 | ~100+ | Logs, media, backups, sandboxes, state files |
| `_holding/infra_ops/` | 0 | ~15 | Dockerfile, docker-compose, config, deploy docs |
| `_holding/prototype_surfaces/` | 0 | 0 | Empty |
| `_holding/archive_candidates/` | 0 | 1 | Single empty Untitled.md |
| `vault/` (top-level) | 0 | ~10 | Memory conversations |
| `logs/` (top-level) | 0 | ~40 | Runtime logs (gitignored) |
| `orchestrator/` (top-level) | 0 | ~5 | Approval state files |
| `.claude/` | 1 | ~50 | Project config, agents, commands, hooks, rules, skills, settings |
| `docs/` | 0 | 3 | Audits only currently |

### Symlinks (all point into _holding/)

| Symlink | Target | Purpose |
|---|---|---|
| `/opt/OS/eos_ai` → | `_holding/runtime_legacy/eos_ai` | Legacy import compatibility |
| `/opt/OS/tests` → | `_holding/runtime_legacy/tests` | Test discovery |
| `/opt/OS/core` → | `_holding/runtime_legacy/core` | Legacy imports |
| `/opt/OS/parsers` → | `_holding/runtime_legacy/parsers` | Legacy imports |
| `/opt/OS/scripts` → | `_holding/runtime_legacy/scripts` | Dev/ops tooling |
| `/opt/OS/services` → | `_holding/runtime_legacy/services` | Runtime entrypoints |
| `/opt/OS/data` → | `_holding/data_artifacts/data` | Runtime state |
| `/opt/OS/.env.sessions` → | `_holding/infra_ops/.env.sessions` | Session env |
| `/opt/OS/.dockerignore` → | `_holding/infra_ops/.dockerignore` | Docker build |
| `/opt/OS/Dockerfile` → | `_holding/infra_ops/Dockerfile` | Docker build |
| `/opt/OS/docker-compose.yml` → | `_holding/infra_ops/docker-compose.yml` | Docker compose |

---

## 2. Corrected Whole-Repo Target Tree

```
repo/
├── umh/                          # Canonical installable UMH package
│   ├── __init__.py               # Public API: from umh import run
│   ├── __main__.py               # Thin shim: imports interface/cli.py
│   │
│   ├── core/                     # Control plane spine + shared infrastructure
│   │   ├── __init__.py
│   │   ├── run.py                # 9-stage control plane loop
│   │   ├── clock.py              # _now_ms() and time utilities
│   │   └── event_bus.py          # EventBus, EventRegistry
│   │
│   ├── protocols/                # All cross-subsystem contracts
│   │   ├── __init__.py
│   │   ├── signals.py            # Signal, SignalBundle, SignalTier
│   │   ├── interpretation.py     # InterpretationResult (currently Intent)
│   │   ├── execution.py          # ExecutionRequest, ExecutionResult
│   │   ├── capabilities.py       # Capability, CapabilitySpec
│   │   ├── adapters.py           # LLMAdapter, ShellAdapter protocols
│   │   ├── governance.py         # GovernanceDecision, AuthorityLevel
│   │   ├── persistence.py        # StorageBackend protocol
│   │   ├── memory.py             # MemoryStore, EpisodicMemory, WorkingMemory protocols
│   │   ├── outcome.py            # Outcome enum, FeedbackEvent
│   │   ├── planning.py           # GoalState, HarnessPlan contracts
│   │   ├── world.py              # WorldUpdate structured type
│   │   ├── workstation.py        # WorkstationProfile, BootSequence
│   │   └── security.py           # AccessPolicy, ThreatBoundary
│   │
│   ├── ontology/                 # Primitive types and validation
│   │   ├── __init__.py
│   │   └── primitives.py         # PrimitiveTag, L0, validation
│   │
│   ├── interpretation/           # Signal classification + intent compilation
│   │   ├── __init__.py
│   │   ├── ingest.py             # classify_input
│   │   └── compiler.py           # compile_intent
│   │
│   ├── world_model/              # Environment state representation
│   │   ├── __init__.py
│   │   ├── types.py              # Entity, Relation, Observation
│   │   ├── model.py              # WorldModel, WorldModelEntry
│   │   ├── substrate.py          # WorldSubstrate
│   │   ├── reasoning.py          # WorldReasoning
│   │   ├── simulation.py         # WorldSimulation
│   │   ├── calibration.py        # WorldCalibration
│   │   ├── dynamics_adapter.py   # WorldDynamicsAdapter
│   │   └── state.py              # WorldStateEngine (DECONTAMINATED)
│   │
│   ├── memory/                   # Intelligence subsystem: semantic/episodic/working memory
│   │   ├── __init__.py
│   │   ├── store.py              # MemoryStore, write/recall/forget APIs
│   │   └── working.py            # Working memory for active session context
│   │
│   ├── storage/                  # Low-level persistence infrastructure
│   │   ├── __init__.py
│   │   └── backend.py            # StorageBackend, InMemoryStorage, key-value ops
│   │
│   ├── planning/                 # Goal management and objective optimization
│   │   ├── __init__.py
│   │   ├── goals.py              # GoalState, GoalRegistry, GoalTracker
│   │   ├── objective.py          # ObjectiveFunction, ObjectiveSet
│   │   └── engine.py             # GoalEngineState, weight adaptation
│   │
│   ├── composition/              # Context assembly for execution
│   │   ├── __init__.py
│   │   ├── types.py              # ContextPriority, ContextSection, ContextResult
│   │   ├── budget.py             # TokenBudget
│   │   └── builder.py            # ContextBuilder
│   │
│   ├── capabilities/             # Capability registry and routing
│   │   ├── __init__.py
│   │   ├── registry.py           # CapabilityRegistry, PerformanceStats
│   │   └── router.py             # route_to_capability, RoutingDecision
│   │
│   ├── adapters/                 # External system bridges
│   │   ├── __init__.py
│   │   ├── llm.py                # OllamaLLMAdapter, HttpLLMAdapter
│   │   ├── null.py               # All null/stub implementations
│   │   └── bridge.py             # Centralized platform adapter discovery
│   │
│   ├── environments/             # Runtime environment detection and adaptation
│   │   ├── __init__.py
│   │   └── detector.py           # Environment detection (CLI, server, embedded)
│   │
│   ├── execution/                # Dispatch and pipeline execution
│   │   ├── __init__.py
│   │   ├── engine.py             # execute() single entry point
│   │   ├── harness.py            # AgentHarness, multi-step orchestration
│   │   ├── pipeline.py           # ExecutionPipeline, composable stages
│   │   ├── stages.py             # StageContext, ExecutionStage protocol
│   │   └── quality.py            # QualityGate
│   │
│   ├── governance/               # Policy, authority, and approval decisions
│   │   ├── __init__.py
│   │   ├── authority.py          # AuthorityLevel, check_governance
│   │   ├── capability.py         # CapabilityEnforcer, ProfileRegistry
│   │   └── governor.py           # ImprovementProposal, Governor
│   │
│   ├── security/                 # Access control, confidentiality, threat boundaries
│   │   ├── __init__.py
│   │   └── access.py             # AccessPolicy, credential isolation
│   │
│   ├── workstation/              # User environment profile and work modes
│   │   ├── __init__.py
│   │   └── profile.py            # WorkstationProfile, WorkMode
│   │
│   ├── observability/            # Traces, decision audit, telemetry
│   │   ├── __init__.py
│   │   └── trace.py              # DecisionTrace
│   │
│   ├── learning/                 # Feedback, strategy adaptation, outcomes
│   │   ├── __init__.py
│   │   ├── feedback.py           # record_outcome, FeedbackEvent
│   │   ├── dynamics.py           # FeedbackDynamics, delayed scores
│   │   └── strategy.py           # StrategyMemory, StrategyStats
│   │
│   └── interface/                # Control surfaces (CLI, future API)
│       ├── __init__.py
│       └── cli.py                # CLI commands
│
├── services/                     # Thin runtime entrypoints ONLY
│   ├── discord_bot.py            # Discord bot entry — delegates to UMH
│   ├── telegram_control.py       # Telegram entry — delegates to UMH
│   └── ...                       # Webhooks, heartbeat, etc.
│
├── tools/                        # Dev/ops tooling scripts ONLY
│   ├── graph/                    # Codebase graph tools
│   ├── ops/                      # Operational scripts
│   ├── auth_monitor/             # Auth monitoring
│   └── scheduled/                # Cron job scripts
│
├── infra/                        # Docker, deploy, env config
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── .dockerignore
│   ├── .env.sessions
│   └── config/                   # Service config files
│
├── docs/                         # Product documentation
│   ├── audits/                   # Architecture audits (this file)
│   ├── architecture/             # ARCHITECTURE.md and related
│   └── plans/                    # Migration plans, roadmaps
│
├── tests/                        # Product tests (NOT inside umh/)
│   ├── unit/                     # UMH unit tests
│   ├── integration/              # Cross-subsystem tests
│   └── legacy/                   # Legacy tests pending migration/deletion
│
├── .claude/                      # Claude Code project config
│   ├── CLAUDE.md                 # Project instructions
│   ├── agents/                   # CC subagent definitions
│   ├── commands/                 # CC slash commands
│   ├── hooks/                    # CC hook scripts
│   ├── rules/                    # CC rules files
│   ├── skills/                   # CC skill definitions
│   └── settings.json             # CC settings
│
├── CLAUDE.md                     # Top-level project instructions
├── CLAUDE.local.md               # Private local instructions (gitignored)
├── pyproject.toml                # Package config (to create)
├── .gitignore
│
└── _holding/                     # TEMPORARY — dissolves completely
    ├── runtime_legacy/           # Legacy eos_ai, core, parsers → extract or archive
    ├── eos_product/              # Agent soul docs, orchestrator → extract to docs/ or archive
    ├── claude_code_harnessing/   # Skills, templates → already in .claude/, verify then archive
    ├── knowledge_vault/          # Obsidian vault → separate repo or archive
    ├── data_artifacts/           # Logs, media, backups → data/ or gitignored runtime
    ├── infra_ops/                # → promoted to infra/
    ├── archive_candidates/       # → delete (empty)
    ├── prototype_surfaces/       # → delete (empty)
    └── unknown_review/           # → triage then delete
```

---

## 3. Corrected UMH Internal Target Tree

### Key corrections from prior report

| Prior Decision | Correction | Reason |
|---|---|---|
| `memory/` → `storage/` | `memory/` stays as intelligence subsystem | Memory = semantic recall, episodic retrieval, working memory. Storage = raw key-value persistence. Categorically different. |
| `storage/` not created | `storage/` created from current `memory/storage.py` | StorageBackend + InMemoryStorage are pure persistence infra, not intelligence. |
| `security/` absorbed into governance | `security/` is its own subsystem | Governance = "should this action happen?" Security = "is this caller authorized? Is this data safe?" Different concerns. |
| `environments/` skipped | `environments/` created as structural placeholder | Core product subsystem. Even with one file, it establishes the boundary for future environment-specific logic. |
| `workstation/` skipped | `workstation/` created as structural placeholder | Same reasoning. WorkstationProfile and WorkMode belong here, not scattered. |

### Subsystem count: 20 packages

```
core/ protocols/ ontology/ interpretation/ world_model/
memory/ storage/ planning/ composition/ capabilities/
adapters/ environments/ execution/ governance/ security/
workstation/ observability/ learning/ interface/
```

Plus `tests/` (external to umh/).

---

## 4. Current-to-Target Mapping (Whole Repo)

### UMH internal mapping (inherits from prior report, with corrections)

| Current Path | Target | Notes |
|---|---|---|
| `umh/__init__.py` | `umh/__init__.py` | Keep, update imports |
| `umh/__main__.py` | `umh/__main__.py` → imports `interface/cli.py` | Thin shim |
| `umh/run.py` | `umh/core/run.py` | Control plane spine |
| `umh/adapters/*` | `umh/adapters/*` | Keep (rename base.py → protocols.py) |
| `umh/capability/*` | `umh/capabilities/*` | Rename package |
| `umh/context/*` | `umh/composition/*` | Rename package |
| `umh/decision/*` | `umh/observability/*` | Rename package |
| `umh/execution/*` | `umh/execution/*` | Keep (move contracts to protocols/) |
| `umh/feedback/*` | `umh/learning/*` | Rename package |
| `umh/goals/*` | `umh/planning/*` | Rename package |
| `umh/governance/*` | `umh/governance/*` | Keep |
| `umh/intent/*` | `umh/interpretation/*` | Merge with signal/ |
| `umh/memory/storage.py` | `umh/storage/backend.py` | **CORRECTED**: This is storage, not memory |
| `umh/memory/` (new) | `umh/memory/` | **NEW**: Intelligence subsystem to build |
| `umh/primitives/*` | `umh/ontology/*` | Rename package |
| `umh/signal/event_bus.py` | `umh/core/event_bus.py` | Core infrastructure |
| `umh/signal/ingest.py, types.py` | `umh/interpretation/*` | Merge with intent/ |
| `umh/strategy/*` | `umh/learning/*` | Merge with feedback/ |
| `umh/world/*` | `umh/world_model/*` | Rename package |
| (new) | `umh/environments/` | Structural placeholder |
| (new) | `umh/security/` | Structural placeholder |
| (new) | `umh/workstation/` | Structural placeholder |

### Repo-level mapping

| Current | Target | Action |
|---|---|---|
| `_holding/runtime_legacy/services/*.py` | `services/` (top-level, no symlink) | Promote. Thin wrappers only — strip any intelligence logic |
| `_holding/runtime_legacy/scripts/` | `tools/` | Rename + promote |
| `_holding/runtime_legacy/core/` | Triage → extract UMH value or archive | Most is legacy action system, tool mastery |
| `_holding/runtime_legacy/parsers/` | Triage → `umh/interpretation/` or archive | Check for unique parsing logic |
| `_holding/runtime_legacy/eos_ai/*.py` (207 files) | Triage per file (see §9) | Some have UMH value, most are legacy |
| `_holding/runtime_legacy/eos_ai/substrate/` (197 files) | Triage per file (see §9) | Substrate was proto-UMH |
| `_holding/runtime_legacy/eos_ai/adapters/` (21 files) | `umh/adapters/` or archive | umh_* files are bridge adapters |
| `_holding/runtime_legacy/tests/` | `tests/` (top-level, no symlink) | Promote. Separate UMH tests from legacy tests |
| `_holding/infra_ops/` | `infra/` | Promote entirely |
| `_holding/eos_product/agents/` | `docs/agents/` or archive | Soul docs are documentation, not runtime |
| `_holding/eos_product/saas/` | Separate repo or archive | Not UMH |
| `_holding/eos_product/orchestrator/` | Archive | Daily logs, historical |
| `_holding/eos_product/ventures/` | Archive | Instance-specific, not platform |
| `_holding/eos_product/knowledge/` | Archive or `docs/` | Knowledge domain docs |
| `_holding/claude_code_harnessing/` | Verify .claude/ has everything, then archive | CC config lives in .claude/ |
| `_holding/knowledge_vault/` | Separate repo or archive | Obsidian vault is not UMH runtime |
| `_holding/data_artifacts/` | Gitignored `data/` dir for runtime, `docs/` for reports | Runtime state should not be in source control |
| `_holding/archive_candidates/` | Delete | Empty (1 blank file) |
| `_holding/prototype_surfaces/` | Delete | Empty |
| `_holding/unknown_review/` | Triage then delete | Unreviewed holding material |
| `vault/` (top-level) | Gitignored runtime data | Memory conversations are runtime state |
| `logs/` (top-level) | Already gitignored | Keep as-is |
| `orchestrator/` (top-level) | Merge into `tools/` or archive | Approval state files |
| `.claude/` | Keep | CC project config is required for development |
| `CLAUDE.md` | Keep, update for UMH | Project instructions |

---

## 5. Control-Plane Invariant Violations

**Invariant:** No signal, decision, action, tool call, device operation,
workflow, memory write, or learning update may bypass the UMH control plane.

### Violations in umh/

| File | Violation | Severity |
|---|---|---|
| `run.py:378-401` `_execute_via_adapter()` | Direct adapter invocation inside the run loop, bypassing execution subsystem | HIGH — execution logic must route through `execution/engine.py` |
| `run.py:394` | Hardcoded `local_python` string match with inline execution | HIGH — all execution must go through capability routing |
| `run.py:397` | Direct `get_adapter("llm")` call bypasses execution contracts | HIGH — adapters must be invoked by execution subsystem only |
| `feedback/loop.py` | Module-level `_feedback_log: list` — in-memory feedback bypasses persistence | MEDIUM — feedback must go through storage/ APIs |

### Violations in legacy code (outside umh/)

| Location | Violation | Severity |
|---|---|---|
| `services/discord_bot.py` | Contains intelligence routing, not just entrypoint delegation | HIGH — must be thin wrapper |
| `eos_ai/execution_spine.py` | Parallel execution spine outside UMH | CRITICAL — superseded by UMH but still imported |
| `eos_ai/agent_runtime.py` | Multi-model router with execution logic | CRITICAL — routing belongs in UMH capabilities/ |
| `eos_ai/model_router.py` | LLM dispatch with fallback chains | HIGH — belongs in UMH adapters/ |
| `eos_ai/authority_engine.py` | Risk classification outside UMH governance | HIGH — governance belongs in UMH |
| `eos_ai/gateway.py` | Message gateway with routing logic | HIGH — routing belongs in UMH |
| `eos_ai/context_builder.py` | Context assembly outside UMH | MEDIUM — superseded by umh/composition/ |
| `eos_ai/substrate/*.py` (197 files) | Entire substrate layer operates outside UMH control plane | CRITICAL — substrate was proto-UMH, now superseded |

---

## 6. eos_ai Contamination in UMH

| File | Import | Type | Severity |
|---|---|---|---|
| `world/state.py:46` | `from eos_ai.decision_trace import DecisionTrace` | TYPE_CHECKING guard | CRITICAL — type dependency on legacy |
| `world/state.py:47` | `from eos_ai.goal_state import GoalRegistry` | TYPE_CHECKING guard | CRITICAL — type dependency on legacy |
| `world/state.py:329` | `from eos_ai.strategy_memory import get_strategy_memory` | Runtime import | CRITICAL — runtime data dependency |
| `goals/interfaces.py:64` | `from eos_ai.adapters.umh_goals import...` | try/except fallback | ACCEPTABLE — adapter discovery pattern |
| `strategy/interfaces.py:64` | `from eos_ai.adapters.umh_strategy import...` | try/except fallback | ACCEPTABLE — adapter discovery pattern |
| `memory/storage.py:62` | `from eos_ai.adapters.umh_storage import...` | try/except fallback | ACCEPTABLE — adapter discovery pattern |
| `execution/interfaces.py:90` | `from eos_ai.adapters.umh_execution import...` | try/except fallback | ACCEPTABLE — adapter discovery pattern |
| `execution/interfaces.py:115` | `from eos_ai.adapters.umh_execution import...` | try/except fallback | ACCEPTABLE — adapter discovery pattern |
| `governance/capability.py:11` | Comment: "Extracted from core.capability" | Comment only | COSMETIC — remove reference |

### Decontamination plan for world/state.py

The three eos_ai imports serve specific purposes:
1. `DecisionTrace` (type hint) → Replace with protocol or `Any` type + runtime duck typing
2. `GoalRegistry` (type hint) → Replace with UMH's own `umh.goals.state.GoalRegistry`
3. `get_strategy_memory()` (runtime) → Replace with protocol-based injection via `umh.strategy.interfaces`

All three can be resolved without behavioral change. The existing UMH types
already provide the needed interfaces.

### Decontamination plan for adapter discovery (4 files)

The try/except pattern is architecturally correct (optional platform binding).
However, all four files duplicate the same pattern. Centralize into
`adapters/bridge.py` with a single `discover_platform_adapter(name)` function.
The individual interfaces still call through it but the import logic lives once.

---

## 7. Symlink / Remnant Strategy

### Symlinks that must persist until import rewrites complete

| Symlink | Blocks on | Can remove when |
|---|---|---|
| `eos_ai` → `_holding/runtime_legacy/eos_ai` | UMH contamination in world/state.py + 4 adapter discovery files | After Wave 0 decontamination + adapter bridge centralization |
| `services` → `_holding/runtime_legacy/services` | Service files need rewrite to delegate to UMH | After services are promoted and rewritten |
| `tests` → `_holding/runtime_legacy/tests` | Tests reference both umh.* and eos_ai.* | After test triage separates UMH tests from legacy |
| `scripts` → `_holding/runtime_legacy/scripts` | Some scripts used by dev workflow | After promotion to tools/ |
| `core` → `_holding/runtime_legacy/core` | Unknown import dependencies | After triage confirms nothing in UMH or services imports core.* |
| `parsers` → `_holding/runtime_legacy/parsers` | Unknown import dependencies | After triage confirms nothing imports parsers.* |
| `data` → `_holding/data_artifacts/data` | Runtime services write here | After data path is reconfigured |

### Symlinks that can be replaced immediately

| Symlink | Action |
|---|---|
| `.dockerignore` → `_holding/infra_ops/.dockerignore` | Move file to `infra/`, update symlink or remove |
| `Dockerfile` → `_holding/infra_ops/Dockerfile` | Move file to `infra/`, update symlink or remove |
| `docker-compose.yml` → `_holding/infra_ops/docker-compose.yml` | Move file to `infra/`, update symlink or remove |
| `.env.sessions` → `_holding/infra_ops/.env.sessions` | Move file to `infra/`, update symlink or remove |

### Remnants for immediate deletion

| Path | Reason |
|---|---|
| `_holding/archive_candidates/` | Contains 1 empty Untitled.md |
| `_holding/prototype_surfaces/` | Empty directory |

---

## 8. Safe Deletion Candidates

These files/directories are confirmed superseded by UMH equivalents
or contain no unique value:

| Path | Superseded by | Confidence |
|---|---|---|
| `_holding/archive_candidates/` | Nothing (empty) | 100% |
| `_holding/prototype_surfaces/` | Nothing (empty) | 100% |
| `_holding/runtime_legacy/eos_ai/world_state.py` | `umh/world/state.py` | HIGH — verify no unique logic |
| `_holding/runtime_legacy/eos_ai/world_model.py` | `umh/world/model.py` | HIGH — verify no unique logic |
| `_holding/runtime_legacy/eos_ai/world_reasoning.py` | `umh/world/reasoning.py` | HIGH — verify no unique logic |
| `_holding/runtime_legacy/eos_ai/world_simulation.py` | `umh/world/simulation.py` | HIGH — verify no unique logic |
| `_holding/runtime_legacy/eos_ai/world_calibration.py` | `umh/world/calibration.py` | HIGH — verify no unique logic |
| `_holding/runtime_legacy/eos_ai/world_dynamics_adapter.py` | `umh/world/dynamics_adapter.py` | HIGH — verify no unique logic |
| `_holding/runtime_legacy/eos_ai/world_substrate.py` | `umh/world/substrate.py` | HIGH — verify no unique logic |
| `_holding/runtime_legacy/eos_ai/world_types.py` | `umh/world/types.py` | HIGH — verify no unique logic |
| `_holding/runtime_legacy/eos_ai/world_pulse.py` | Likely dead code | MEDIUM — verify |
| `_holding/runtime_legacy/eos_ai/intent_compiler.py` | `umh/intent/compiler.py` | HIGH — verify |
| `_holding/runtime_legacy/eos_ai/intent_router.py` | `umh/intent/compiler.py` | MEDIUM — may have unique routing logic |
| `_holding/runtime_legacy/eos_ai/signal_ingestion.py` | `umh/signal/ingest.py` | HIGH — verify |
| `_holding/runtime_legacy/eos_ai/cognitive_loop.py` | `umh/core/run.py` | HIGH — CLAUDE.md says deprecated |
| `_holding/runtime_legacy/eos_ai/decision_trace.py` | `umh/decision/trace.py` | HIGH — verify |

**Rule: No deletion without diff verification.** Every "safe" deletion
must be preceded by `diff` between the legacy file and the UMH equivalent
to confirm no unique logic was lost.

---

## 9. Extraction-Before-Deletion Candidates

These legacy files contain unique UMH-relevant logic that must be
extracted into the correct UMH subsystem before the legacy file
can be archived or deleted:

| Legacy File | Unique Value | Extract To |
|---|---|---|
| `eos_ai/model_router.py` | Multi-model fallback chain, provider health | `umh/adapters/llm.py` or new `umh/adapters/model_router.py` |
| `eos_ai/authority_engine.py` | 4 risk classes, change validation | `umh/governance/authority.py` (merge) |
| `eos_ai/execution_spine.py` | SpineResult contract, stage pipeline | `umh/execution/` (verify overlap) |
| `eos_ai/context_builder.py` | Context assembly patterns | `umh/composition/builder.py` (verify overlap) |
| `eos_ai/memory.py` | Neon-backed memory writes | `umh/memory/` (new subsystem) |
| `eos_ai/memory_fabric.py` | Memory evolution, semantic memory | `umh/memory/` (new subsystem) |
| `eos_ai/causal_memory.py` | Causal attribution for memory | `umh/memory/` or `umh/learning/` |
| `eos_ai/strategy_memory.py` | Strategy stats persistence | Already in `umh/strategy/memory.py` — verify diff |
| `eos_ai/strategy_pattern_memory.py` | Pattern-based strategy recall | `umh/learning/strategy.py` (extract patterns) |
| `eos_ai/goal_state.py` | Goal management | Already in `umh/goals/state.py` — verify diff |
| `eos_ai/feedback_loop.py` | Outcome recording | Already in `umh/feedback/loop.py` — verify diff |
| `eos_ai/calibration.py` | World calibration | Already in `umh/world/calibration.py` — verify diff |
| `eos_ai/db.py` | Neon connection + RLS | `umh/storage/` or `umh/adapters/neon.py` |
| `eos_ai/session_state.py` | Session resume context | `umh/workstation/` or `umh/environments/` |
| `eos_ai/system_context.py` | System context + change validation | `umh/governance/` or `umh/environments/` |
| `eos_ai/event_bus.py` | Event bus (legacy version) | Already in `umh/signal/event_bus.py` — verify diff |
| `eos_ai/confidentiality.py` | Data classification, access rules | `umh/security/` (new subsystem) |
| `eos_ai/adapters/umh_*.py` (4 files) | Platform bridge adapters | Stay outside UMH but move to a proper platform/ location |
| `eos_ai/substrate/workstation_*.py` | Workstation profiles, bootstrap | `umh/workstation/` (new subsystem) |
| `eos_ai/substrate/operator_*.py` | Operator session, presence, approvals | `umh/interface/` or `umh/workstation/` |

---

## 10. Corrected Migration Sequence

### Wave 0: Decontaminate (no file moves, no renames)

**Gate:** `python3 -c "import umh; print('OK')"` works with eos_ai symlink removed.

1. Fix `world/state.py` — remove all 3 `from eos_ai` imports:
   - Replace `DecisionTrace` type hint with `Any` or a local protocol
   - Replace `GoalRegistry` type hint with `umh.goals.state.GoalRegistry`
   - Replace `get_strategy_memory()` call with protocol injection via
     `umh.strategy.interfaces.get_strategy_persistence()`
2. Centralize adapter discovery — create `umh/adapters/bridge.py` with
   `discover_platform_adapter(name: str)` that handles the try/except pattern.
   Update `goals/interfaces.py`, `strategy/interfaces.py`, `memory/storage.py`,
   `execution/interfaces.py` to call through it.
3. Remove `governance/capability.py:11` comment referencing `core.capability`.
4. Fix `run.py` hard rule violations:
   - Extract `_execute_via_adapter()` into `execution/engine.py`
   - Remove hardcoded `local_python` string match
   - Route all execution through `execution/engine.py` → adapter
5. Fix `feedback/loop.py` — replace module-level `_feedback_log` list with
   storage-backed persistence via `storage/backend.py`.

**Test gate:** All existing UMH tests pass. `python3 -c "import umh"` works
without eos_ai on sys.path.

### Wave 1: Create infrastructure (new files and directories only)

6. Create `umh/core/__init__.py`
7. Create `umh/core/clock.py` — extract `_now_ms()` from run.py, engine.py,
   harness.py, pipeline.py
8. Create `umh/protocols/__init__.py` and protocol files (contracts only,
   no implementations)
9. Create `umh/storage/__init__.py` and `umh/storage/backend.py` — move
   `StorageBackend` and `InMemoryStorage` from `memory/storage.py`
10. Create `umh/memory/__init__.py` and `umh/memory/store.py` — define
    `MemoryStore` protocol (semantic write/recall/forget)
11. Create `umh/environments/__init__.py` and `umh/environments/detector.py` —
    minimal environment detection
12. Create `umh/workstation/__init__.py` and `umh/workstation/profile.py` —
    `WorkstationProfile` and `WorkMode` types
13. Create `umh/security/__init__.py` and `umh/security/access.py` —
    `AccessPolicy` protocol
14. Create `umh/adapters/null.py` — consolidate all null stubs
15. Create `umh/interface/__init__.py` and `umh/interface/cli.py` —
    move `__main__.py` contents

**Test gate:** All existing tests pass. New subsystems importable.

### Wave 2: Promote non-umh/ directories (no package renames yet)

16. Create `infra/` and move infra files from `_holding/infra_ops/`
17. Remove infra symlinks (.dockerignore, Dockerfile, docker-compose.yml,
    .env.sessions)
18. Create `tools/` and promote scripts from `_holding/runtime_legacy/scripts/`
19. Remove `scripts` symlink
20. Promote test files: copy UMH-specific tests from
    `_holding/runtime_legacy/tests/test_umh_*.py` to `tests/unit/`
21. Delete `_holding/archive_candidates/` and `_holding/prototype_surfaces/`
22. Triage `_holding/unknown_review/` — archive or delete

**Test gate:** `python3 -m pytest tests/` passes. Docker builds still work.

### Wave 3: UMH package renames (update all internal imports)

23. `primitives/` → `ontology/`
24. `signal/ingest.py` + `signal/types.py` → `interpretation/`
25. `intent/` → merge into `interpretation/`
26. Move `signal/event_bus.py` → `core/event_bus.py`
27. `capability/` → `capabilities/`
28. `context/` → `composition/`
29. `decision/` → `observability/`
30. `feedback/` → `learning/`
31. `strategy/` → merge into `learning/`
32. `goals/` → `planning/`
33. `world/` → `world_model/`
34. Move `run.py` → `core/run.py`, update `__init__.py`
35. Move execution contracts to `protocols/execution.py`
36. Move adapter protocols to `protocols/adapters.py`
37. Global import fixup across all umh/ files

**Test gate:** `python3 -c "from umh import run; print('OK')"`. All UMH tests
pass under new import paths. No `from umh.signal.` or `from umh.capability.`
imports remain.

### Wave 4: Create missing contracts

38. `WorldUpdate` type in `protocols/world.py`
39. `Outcome` proper enum in `protocols/outcome.py`
40. `BootSequence` protocol in `protocols/workstation.py`
41. `WorkMode` enum in `protocols/workstation.py` or `workstation/profile.py`
42. `MemoryStore` refined protocol in `protocols/memory.py`
43. `AccessPolicy` protocol in `protocols/security.py`

**Test gate:** All protocols importable. Type checking passes.

### Wave 5: Service entrypoint rewrite

44. Rewrite `services/discord_bot.py` as thin UMH entry:
    receive message → `umh.run(message)` → send response
45. Rewrite `services/telegram_control.py` similarly
46. Verify no intelligence/routing/planning logic remains in services/
47. Remove `services` symlink, promote to top-level

**Test gate:** Services start and delegate to UMH. No eos_ai imports in services.

### Wave 6: Legacy triage and extraction

48. Diff every "safe deletion candidate" against UMH equivalent
49. Extract unique value from extraction-before-deletion candidates (§9)
50. For each extraction:
    - Read legacy file
    - Identify unique logic not in UMH
    - Port to correct UMH subsystem
    - Verify with tests
51. Archive triaged files to `_holding/archived/` with date stamp
52. Verify `core` and `parsers` symlinks have no remaining consumers
53. Remove remaining symlinks

**Test gate:** Full test suite. `find /opt/OS -maxdepth 1 -type l` returns nothing.

### Wave 7: _holding/ dissolution

54. Move any remaining useful files to their final locations
55. Verify `_holding/` contains only archived material
56. Move entire `_holding/` to an `archive/` directory or delete
57. Create `pyproject.toml` for UMH package

**Test gate:** `pip install -e .` installs UMH package. `python3 -m umh status`
works from any directory.

---

## 11. Test Gates Summary

| Wave | Gate Command | What it proves |
|---|---|---|
| 0 | `python3 -c "import umh"` without eos_ai on path | UMH is standalone |
| 0 | `python3 -m pytest tests/test_umh_*.py` | No regressions |
| 1 | `python3 -c "from umh.storage.backend import StorageBackend"` | New subsystems exist |
| 2 | `docker build -f infra/Dockerfile .` | Infra promotion works |
| 3 | `grep -r "from umh\.\(signal\|capability\|context\|decision\|feedback\|strategy\|goals\|memory\|primitives\|intent\|world\)\." umh/` returns nothing | All renames complete |
| 4 | `python3 -c "from umh.protocols import *"` | All contracts importable |
| 5 | `grep -r "from eos_ai\|import eos_ai" services/` returns nothing | Services are clean |
| 6 | `find /opt/OS -maxdepth 1 -type l` returns nothing | All symlinks removed |
| 7 | `pip install -e . && python3 -m umh status` | Package is installable |

---

## 12. Risks

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| `world/state.py` decontamination breaks state extraction | UMH can't extract world state | MEDIUM | Port logic to use UMH's own GoalRegistry and protocol-based strategy access. Test with existing fixtures. |
| Service rewrite breaks running production bots | Discord/Telegram bots go down | HIGH | Rewrite one service at a time. Keep symlink active until verified. |
| Package renames break all 170+ legacy tests | Loss of test coverage validation | LOW | Legacy tests already point at old eos_ai paths, not umh. UMH tests (~20) are the real gate. |
| `_holding/` contains unique logic we delete prematurely | Permanent data loss | MEDIUM | Never delete without diff. Wave 6 is explicitly triage-then-extract-then-archive. |
| Docker/infra paths change and break running containers | Service outage | MEDIUM | Update docker-compose.yml paths before removing infra symlinks. Test build before deploy. |
| Memory subsystem (new) has no implementation yet | Empty subsystem forever | LOW | Start with protocol + one in-memory implementation. Extract from eos_ai/memory.py in Wave 6. |

---

## 13. Final Recommendation

Execute waves 0-1 immediately. They are safe (no file moves, no renames)
and they establish the foundation everything else depends on:

- **Wave 0** eliminates the one critical contamination and fixes hard rule
  violations. After this, UMH is genuinely standalone.
- **Wave 1** creates the structural placeholders that the previous report
  incorrectly skipped (memory, storage, environments, workstation, security).

Waves 2-3 can follow once Wave 0-1 is verified. These are mechanical
(file moves + import updates) and low risk.

Waves 4-7 are medium-term. The service rewrite (Wave 5) is the highest-risk
step in the entire sequence and should be done one service at a time with
rollback capability.

Do not attempt broad package renames (Wave 3) until contamination is fixed
(Wave 0) and infrastructure is in place (Wave 1). Renaming before
decontamination multiplies the merge conflict surface area.
