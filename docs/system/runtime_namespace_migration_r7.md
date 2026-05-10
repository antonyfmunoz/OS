# Runtime Namespace Migration — R7 Report

> Phase: 96.8CP — 2026-05-10
> Commit: root-migration-r7
> Type: Planning/analysis only — no code changes

---

## Objective

Design the controlled migration plan for renaming `eos_ai/` to
`umh_runtime/`, including full dependency mapping, compatibility
shim design, phased sequencing, and rollback strategy.

---

## 1. eos_ai Import Graph

### 1.1 Total Import Sites by Type

| Type | Count | Notes |
|------|-------|-------|
| `from eos_ai.*` imports | 2,687 | Python import statements |
| `import eos_ai.*` (bare) | 39 | Module-level bare imports |
| String-based refs (`mock.patch`, `importlib`) | 221 | Cannot be caught by import rewriter |
| Filesystem path refs (`eos_ai/`) | 201 | Path strings in Python code |
| Shell script refs | 85 | Inline Python + path refs |
| Docker/config refs | 4 | `docker-compose.yml` env_file |
| Crontab entries | 2 | Live cron jobs |
| `python3 -m eos_ai.*` invocations | 20 | Module-mode execution |
| `eos_ai/.env` references | 256 | Env file location refs |
| **Total Python import sites** | **2,726** | from + bare |
| **Total migration surface** | **~3,515** | All ref types |

### 1.2 Consumer Classification

| Consumer | `from eos_ai` Count | Category |
|----------|---------------------|----------|
| `eos_ai/` (self) | 1,448 | Internal self-reference |
| `scripts/` | 470 | Operations/smoke tests |
| `tests/` | 380 | Test suite |
| `services/` | 304 | Live entrypoints |
| `archive/` | 65 | Historical (frozen) |
| `core/` | 16 | Substrate contracts (circular dep) |
| `saas/` | 3 | SaaS product |
| `templates/` | 1 | Template files |

### 1.3 Import Depth Distribution

| Depth | Count | Example |
|-------|-------|---------|
| 1 level (`eos_ai.module`) | 1,337 | `from eos_ai.db import get_conn` |
| 2 levels (`eos_ai.sub.module`) | 1,274 | `from eos_ai.substrate.storage import get_storage` |
| 3 levels | 73 | `from eos_ai.platforms.eos.roles import EOSRole` |
| 4 levels | 2 | Deep platform imports |
| 5 levels | 1 | Single deep chain |

### 1.4 Critical-Path Modules (Top 20 by Import Count)

| Module | Import Count | Consumer Spread | Migration Risk |
|--------|-------------|-----------------|----------------|
| `substrate.*` | 690 | All consumers | HIGH — shim layer, 88 test files |
| `transport.*` | 594 | All consumers | HIGH — canonical subsystem |
| `context` | 254 | All consumers | HIGH — universal dependency |
| `db` | 186 | All consumers | HIGH — universal dependency |
| `model_router` | 78 | scripts, services, eos_ai | MEDIUM |
| `platforms.*` | 61 | tests, eos_ai | LOW — mostly dormant |
| `gws_connector` | 60 | scripts, services | MEDIUM |
| `memory` | 49 | services, eos_ai, core | MEDIUM |
| `agent_runtime` | 48 | services, scripts, eos_ai | MEDIUM |
| `business_instance` | 38 | services, eos_ai | MEDIUM |
| `interfaces.*` | 35 | tests, eos_ai | LOW — dormant |
| `gateway` | 26 | services, scripts, eos_ai | MEDIUM |
| `portfolio_advisor` | 20 | services, scripts | LOW |
| `cognitive_loop` | 18 | scripts, services | LOW |
| `goal_selector` | 16 | tests, eos_ai | LOW |
| `runtime.*` | 15 | services, tests | LOW |
| `discord_utils` | 15 | services, scripts | LOW |
| `event_bus` | 14 | services, eos_ai | LOW |
| `person_recognition` | 13 | services, scripts | LOW |
| `primitives` | 12 | scripts, eos_ai | LOW |

---

## 2. External Consumer Graph

### 2.1 services/ (304 imports — LIVE, CRITICAL)

Primary consumer of runtime intelligence. All imports are
load-bearing for the Discord bot.

**Top dependencies:**
- `context` (63) — `load_context_from_env`, `EOSContext`
- `gws_connector` (15) — `GWSConnector`
- `db` (14) — `get_conn`
- `gateway` (13) — `EOSGateway`
- `memory` (8) — `AgentMemory`
- `model_router` (7) — `get_router`, `TaskType`
- `founder_rate` (7), `doc_creator` (7), `coordination_engine` (7)

**Dynamic imports (special handling needed):**
- `services/discord_bot.py:787` — `__import__("eos_ai.agent_teams")`
- `services/discord_bot.py:882` — `__import__("eos_ai.agent_teams")`
- `services/discord_bot.py:3247` — `__import__("eos_ai.world_pulse")`

### 2.2 scripts/ (470 imports — OPERATIONS)

Mix of cron scripts, smoke tests, and utilities.
Many use `import eos_ai.module as alias` pattern.

**Top dependencies:**
- `substrate.*` (45+ distinct submodules)
- `context` (24)
- `db` (19)
- `model_router` (14)
- `gws_connector` (12)

### 2.3 tests/ (380 imports — TESTING)

Test suite — breakage is recoverable but noisy.

**Special concern — mock.patch strings:**
221 string-based module references like:
```python
with patch("eos_ai.substrate.local_executor.execute_command", ...):
```
These are NOT caught by import aliasing or re-exports.
They must be updated with a string-replacement pass.

### 2.4 core/ (16 imports — CIRCULAR DEPENDENCY)

`core/` is the substrate contracts layer. It should NOT depend on
`eos_ai/` (the runtime). These 16 imports create a circular dependency:

| File | Imports |
|------|---------|
| `core/execution_contract.py` | `context`, `db`, `substrate.execution_trace`, `gateway`, `authority_engine`, `memory`, `agent_runtime` |
| `core/coord_assignment.py` | `embedder` |
| `core/semantic_space.py` | `embedder` |
| `core/agent_harness.py` | `memory`, `model_router`, `agent_runtime` |
| `core/workstation/*.py` | `substrate.memory_scope_contracts` |
| `core/action_system/policy.py` | `authority_engine` |

**Resolution strategy:** These must be inverted during migration:
1. Extract shared interfaces (e.g., `get_conn`, `load_context_from_env`)
   into `core/` where they canonically belong
2. Or accept the circular dep and use lazy imports (already partially
   done — `core/execution_contract.py` uses inline imports)

### 2.5 archive/ (65 imports — FROZEN)

Historical code. Do NOT migrate — leave as-is with dead imports.
Archive code is expected to break if eos_ai/ is removed.

---

## 3. Internal Self-Reference Graph

### 3.1 eos_ai/ Internal Imports (1,448)

**By subdirectory (source of import):**

| Subdirectory | Self-Import Count | Pattern |
|-------------|-------------------|---------|
| `transport/` | 453 | Canonical transport, heavy cross-refs |
| `substrate/` | 165 | Shim layer → transport |
| `orchestrator/` | 71 | Orchestration logic |
| `gateway/` | 54 | Message classification |
| `cognitive_loop/` | 25 | Core loop |
| `context_builder/` | 24 | Context assembly |
| `email_gps/` | 22 | Email intelligence |
| `voice_interface/` | 20 | Voice pipeline |
| `meetings/` | 19 | Meeting intelligence |
| `memory/` | 17 | Persistence |
| `event_bus/` | 17 | Event system |

### 3.2 Package Structure

eos_ai uses **implicit namespace packages** (no top-level `__init__.py`).
Only two subdirectories have `__init__.py`:
- `eos_ai/substrate/__init__.py` — shim re-exports
- `eos_ai/transport/__init__.py` — canonical transport

The migration must preserve implicit-namespace behavior for
`umh_runtime/` (no top-level `__init__.py`).

---

## 4. Circular Dependency Audit

### 4.1 core/ ↔ eos_ai/ Bidirectional Dependency

```
core/ ─── 16 imports ───→ eos_ai/
eos_ai/ ── 25 imports ──→ core/
```

**core/ → eos_ai/ (problematic direction):**
- `core/execution_contract.py` → `eos_ai.context`, `eos_ai.db`,
  `eos_ai.gateway`, `eos_ai.authority_engine`, `eos_ai.memory`
- `core/agent_harness.py` → `eos_ai.memory`, `eos_ai.model_router`
- `core/coord_assignment.py` → `eos_ai.embedder`
- `core/workstation/*.py` → `eos_ai.substrate.memory_scope_contracts`

**eos_ai/ → core/ (expected direction):**
- `eos_ai/transport/` → `core.environment_bridge`, `core.runtime`,
  `core.execution_contract`
- `eos_ai/interfaces/` → `core.governance`, `core.execution`,
  `core.runtime`, `core.state`, `core.registry`, `core.control_plane_router`

### 4.2 Circular Dependency Resolution

The core/ → eos_ai/ imports are primarily:
1. **Shared primitives** (`get_conn`, `load_context_from_env`, `EOSContext`)
   — these should live in core/ anyway
2. **Lazy imports** for optional functionality (gateway, authority_engine)
   — already inside function bodies, so not import-cycle problems

**Recommendation:** During the rename, migrate `db.py`, `context.py`,
and `embedder.py` exports into `core/` as canonical locations, with
`umh_runtime/` re-exporting them for backward compatibility.

---

## 5. Package Boundary Audit

### 5.1 Existing umh/ Namespace

A `umh/` directory already exists at repo root, but it is **archived**:

```python
# umh/__init__.py
raise ImportError(
    "umh/ has been archived to archive/umh_reference/ ..."
)
```

11,433 references to `from umh` exist, all in `tests/legacy/` — these
import from the archived package and are expected to fail. The `umh/`
slot is occupied but dead.

### 5.2 Namespace Collision Analysis

| Candidate | Collision Risk | Assessment |
|-----------|---------------|------------|
| `umh_runtime/` | NONE | No existing directory, no imports |
| `umh/` | HIGH | Directory exists (archived), 11K+ legacy refs |
| `runtime/` | HIGH | `eos_ai/runtime/` already exists as subdirectory |
| `substrate/` | HIGH | `eos_ai/substrate/` already exists as subdirectory |
| `substrate_runtime/` | NONE | No existing directory |

---

## 6. Compatibility Shim Design

### 6.1 Architecture

```
umh_runtime/                   ← new canonical location
  context.py                   ← actual code lives here
  db.py
  model_router.py
  ...
  transport/                   ← moved from eos_ai/transport/
  substrate/                   ← moved from eos_ai/substrate/

eos_ai/                        ← compatibility shim (temporary)
  __init__.py                  ← empty or warning
  context.py                   ← from umh_runtime.context import *
  db.py                        ← from umh_runtime.db import *
  model_router.py              ← from umh_runtime.model_router import *
  ...
  transport/__init__.py        ← from umh_runtime.transport import *
  substrate/__init__.py        ← from umh_runtime.substrate import *
```

### 6.2 Shim Module Template

Each shim module in `eos_ai/` follows this pattern:

```python
"""Compatibility shim — canonical location: umh_runtime.{module}"""
import warnings
warnings.warn(
    "eos_ai.{module} is deprecated. Use umh_runtime.{module}.",
    DeprecationWarning,
    stacklevel=2,
)
from umh_runtime.{module} import *  # noqa: F401,F403
```

### 6.3 Shim Lifecycle

| Phase | Duration | Behavior |
|-------|----------|----------|
| Phase A — Silent shim | 2 weeks | Re-exports only, no warning |
| Phase B — Deprecation warnings | 2 weeks | DeprecationWarning on import |
| Phase C — Loud warnings | 1 week | RuntimeWarning, log to stderr |
| Phase D — Removal | — | Delete eos_ai/, shim gone |

**For this project (solo founder):** Phases A+B can be compressed.
The shim exists only to prevent breakage during migration, not for
external consumers. Recommended: 1 week silent, then remove.

### 6.4 Dynamic Import Handling

These cannot be handled by shims alone:

| Pattern | Count | Strategy |
|---------|-------|----------|
| `__import__("eos_ai.X")` | 3 | String replacement |
| `importlib.import_module("eos_ai.X")` | 2 | String replacement |
| `importlib.util.find_spec("eos_ai.X")` | 3 | String replacement |
| `mock.patch("eos_ai.X.Y.Z")` | 221 | Bulk string replacement |
| `python3 -m eos_ai.X` | 20 | Shell/doc string replacement |

---

## 7. Phased Migration Sequencing

### Phase R8a — Create umh_runtime/ Package (LOW RISK)

**Actions:**
1. Create `umh_runtime/` directory (no `__init__.py` — implicit namespace)
2. Copy (not move) all top-level `.py` files from `eos_ai/` to `umh_runtime/`
3. Copy `transport/` and `substrate/` subdirectories
4. Verify: `python3 -c "from umh_runtime.db import get_conn; print('ok')"`

**Files affected:** ~116 modules copied
**Risk:** NONE — additive only, nothing changes
**Rollback:** `rm -rf umh_runtime/`

### Phase R8b — Install Compatibility Shims (LOW RISK)

**Actions:**
1. Replace each `eos_ai/*.py` with a shim that re-exports from `umh_runtime`
2. Preserve `eos_ai/substrate/__init__.py` and `eos_ai/transport/__init__.py`
   as shims
3. Verify: all existing imports still work through shims
4. Run full test suite — expect 8558 pass, 27 fail (pre-existing)

**Files affected:** ~116 shim files
**Risk:** LOW — if any import breaks, the shim is wrong
**Rollback:** `git checkout HEAD -- eos_ai/`

### Phase R8c — Migrate External Consumers (MEDIUM RISK)

**Sequencing (safest → riskiest):**

1. **archive/** (65 imports) — skip, leave broken
2. **tests/** (380 imports) — bulk sed, verify with test run
3. **scripts/** (470 imports) — bulk sed, verify with smoke tests
4. **core/** (16 imports) — manual, resolve circular deps
5. **services/** (304 imports) — manual, test each service

**For each consumer batch:**
```bash
# Replace from eos_ai → from umh_runtime
find <dir> -name '*.py' -exec sed -i \
  's/from eos_ai\./from umh_runtime./g' {} +
# Replace import eos_ai → import umh_runtime
find <dir> -name '*.py' -exec sed -i \
  's/import eos_ai\./import umh_runtime./g' {} +
# Verify
python3 -m pytest tests/ -x --tb=short
```

### Phase R8d — Migrate Internal Self-References (HIGH RISK)

**Actions:**
1. Update all `from eos_ai.*` imports within `umh_runtime/` to use
   `from umh_runtime.*` (relative or absolute)
2. This is the largest batch (1,448 imports)
3. Consider using relative imports within umh_runtime/ to reduce
   future rename impact

**Risk:** HIGH — self-referential imports are the most fragile
**Rollback:** `git checkout HEAD -- umh_runtime/`

### Phase R8e — Migrate String-Based References (MEDIUM RISK)

**Actions:**
1. `mock.patch("eos_ai.X")` → `mock.patch("umh_runtime.X")` (221 sites)
2. `__import__("eos_ai.X")` → `__import__("umh_runtime.X")` (3 sites)
3. `importlib.*("eos_ai.X")` → `importlib.*("umh_runtime.X")` (5 sites)
4. Filesystem paths `eos_ai/` → `umh_runtime/` (201 sites)

### Phase R8f — Migrate Shell/Config/Deployment (MEDIUM RISK)

**Actions:**
1. Shell scripts: `eos_ai` → `umh_runtime` in Python contexts (85 sites)
2. Docker compose: `eos_ai/.env` → `umh_runtime/.env` (3 refs)
3. Crontab: 2 entries with `eos_ai` paths
4. `python3 -m eos_ai.X` → `python3 -m umh_runtime.X` (20 sites)
5. Skills/commands: `eos_ai/.env` references (12+ files)

### Phase R8g — Remove Compatibility Shims (LOW RISK)

**Actions:**
1. Delete all shim files in `eos_ai/`
2. Remove `eos_ai/` directory entirely
3. Verify: `test_umh_wave9_wrapper_removal.py` passes
4. Run full test suite

**Blocker:** All prior phases must be complete
**Risk:** LOW if all consumers migrated

### Phase R8h — Env File Migration (DEPLOYMENT)

**Actions:**
1. Move `eos_ai/.env` → `umh_runtime/.env` (or consolidate to root `.env`)
2. Update all `load_dotenv('*/eos_ai/.env')` references (256 sites)
3. Update Docker compose `env_file:` entries
4. Update crontab entries

**Recommendation:** Consolidate to single root `.env` file during
this migration rather than maintaining `umh_runtime/.env`.

---

## 8. Rollback Strategy

### Per-Phase Rollback

Each phase is independently reversible via `git checkout HEAD -- <scope>`.

### Full Rollback

If the migration fails at any point after R8b:
1. `git checkout HEAD -- eos_ai/` (restores original modules)
2. `rm -rf umh_runtime/` (removes new package)
3. All imports revert to working state

### Safety Net: Compatibility Shim Period

During phases R8b through R8f, both `eos_ai.*` and `umh_runtime.*`
imports work. This provides a safety window where:
- Old code continues to work
- New code uses new namespace
- Mixed state is valid

---

## 9. Namespace Recommendation Comparison

| Criterion | `umh_runtime/` | `runtime/` | `umh/` | `substrate_runtime/` |
|-----------|---------------|-----------|--------|---------------------|
| Collision risk | NONE | HIGH (exists as subdir) | HIGH (archived dir) | NONE |
| Clarity | High — "UMH's runtime" | Ambiguous — generic | Ambiguous — could be anything | Verbose but clear |
| Consistency with docs | Matches R6 recommendation | No | Conflicts with archive | No doc precedent |
| Import ergonomics | `from umh_runtime.db` | `from runtime.db` | `from umh.db` | `from substrate_runtime.db` |
| Length (chars) | 11 | 7 | 3 | 17 |
| Future-proof | Yes — identity in name | No — too generic | Risk of archive confusion | Yes but verbose |
| Existing references | 10 (all in docs, planned) | 0 | 11,433 (all legacy/dead) | 0 |

---

## 10. Final Recommendation

### Recommended namespace: `umh_runtime/`

**Rationale:**
1. Zero collision risk — no existing directory or imports
2. Consistent with R6 documentation and eos_ai/README_STATUS.md recommendation
3. Self-documenting — "UMH runtime" is unambiguous
4. Matches the architectural distinction: `core/` = contracts, `umh_runtime/` = live intelligence
5. All 10 existing references in docs already use this name

### Migration order recommendation:

```
R8a (create)  →  R8b (shims)  →  R8c (external)  →
R8d (internal)  →  R8e (strings)  →  R8f (deploy)  →
R8g (cleanup)  →  R8h (env)
```

### Estimated effort:

| Phase | Files | Effort | Risk |
|-------|-------|--------|------|
| R8a — Create package | 116 | LOW | NONE |
| R8b — Install shims | 116 | LOW | LOW |
| R8c — External consumers | ~1,170 imports across ~300 files | MEDIUM | MEDIUM |
| R8d — Internal self-refs | 1,448 imports across ~200 files | HIGH | HIGH |
| R8e — String-based refs | ~450 sites across ~100 files | MEDIUM | MEDIUM |
| R8f — Shell/config/deploy | ~130 sites across ~30 files | MEDIUM | MEDIUM |
| R8g — Remove shims | 116 files deleted | LOW | LOW |
| R8h — Env file | ~260 sites across ~40 files | MEDIUM | MEDIUM |
| **Total** | **~3,500 sites** | **~4-6 hours** | — |

### Blockers:

1. **Physical rename /opt/OS → /opt/UMH should happen first** (or simultaneously)
   — reduces confusion about what "UMH" means at filesystem level
2. **Docker compose volume mounts** reference `eos_ai/.env` — must coordinate
   with container restart
3. **Crontab entries** — must be updated atomically (2 entries)
4. **core/ → eos_ai/ circular dependency** — must resolve before or during R8c

### Pre-requisites satisfied:

- [x] R1 — UMH_ROOT env chain (core/paths.py)
- [x] R2 — Runtime bootstrap (193 files)
- [x] R3 — Runtime filesystem refs (154 files)
- [x] R4 — Test topology (179 files)
- [x] R5 — Deployment infrastructure (27 files)
- [x] R6 — Semantic identity (8 docs)
- [x] R7 — Namespace migration plan (this document)
- [ ] R8a-h — Physical namespace migration

---

## Appendix A: Unique eos_ai Submodules (116)

<details>
<summary>Full list of importable top-level modules</summary>

accountability, agent_hierarchy, agent_messages, agent_runtime,
agent_teams, ai_identity, authority_engine, browser_agent,
business_instance, buyback_rate, cc_sdk, ceo_agent,
ceo_intelligence, ceo_operational_standards, channel,
claude_skill_registry, cognitive_loop, competitive_intel,
confidentiality, context, context_builder, context_compaction,
coordination_engine, daily_sync, db, decision_log,
delegation_tracker, discord_utils, doc_creator, document_filer,
drip_matrix, ea_operational_standards, email_gps, email_reviewer,
embedder, embedding_engine, eod_closing_loop, error_handler,
event_bus, event_manager, evolution_engine, execution_engine,
execution_loop, execution_spine, expense_tracker, feedback_loop,
founder_capture, founder_rate, gateway, goal_selector,
gws_connector, gws_scanner, harness_registry, higgsfield_client,
human_intelligence, ideal_week, input_intelligence, intent_router,
interfaces, knowledge_domains, knowledge_graph, knowledge_integrator,
knowledge_layers, martell_patterns, media_processor, meetings,
memory, model_preferences, model_router, notebooklm_sync,
notion_publisher, notion_sync, okr_tracker, onboarding_backfill,
onboarding_engine, orchestrator, os_registry, os_trinity,
output_validator, pattern_engine, perfect_week, person_recognition,
personal_admin, platforms, portfolio_advisor,
portfolio_advisor_standards, primitives, principle_engine,
proactive_engine, provider_health, quality_gate, reality_context,
reality_engine, research_engine, runtime, scrapling_connector,
self_awareness, session_state, setup_wizard, signal_hierarchy,
skill_improvement, skill_registry, skill_registry_v2, stage_manager,
stakeholder_map, status, strategy_engine, subscription_tracker,
substrate, system_health, task_executor, task_yield_matrix,
template_library, template_registry, tenant, transport,
travel_manager, trinity, user_model, venture_knowledge,
voice_engine, voice_interface, week_architect, workflow_engine,
world_model, world_pulse
</details>

## Appendix B: Dynamic Import Sites (Require Manual Migration)

| File | Line | Pattern |
|------|------|---------|
| `services/discord_bot.py` | 787 | `__import__("eos_ai.agent_teams")` |
| `services/discord_bot.py` | 882 | `__import__("eos_ai.agent_teams")` |
| `services/discord_bot.py` | 3247 | `__import__("eos_ai.world_pulse")` |
| `eos_ai/transport/discord_voice_playback.py` | 93 | `importlib.import_module("eos_ai.voice_engine")` |
| `eos_ai/research_engine.py` | 545 | `import eos_ai.agent_runtime as _ar` (conditional) |
| `scripts/substrate_workflow_delegation_smoke_test.py` | 460 | `importlib.util.find_spec("eos_ai.substrate.workflow_delegation")` |
| `scripts/substrate_workflow_delegation_smoke_test.py` | 490 | `importlib.util.find_spec("eos_ai.substrate.workflow_delegation")` |
| `scripts/substrate_workflow_delegation_smoke_test.py` | 537 | `importlib.util.find_spec("eos_ai.substrate.discord_text_transport")` |
| `scripts/substrate_execution_trace_smoke_test.py` | 278 | `importlib.import_module("eos_ai.substrate.execution_trace")` |

## Appendix C: Wave-9 End-State Test

`tests/legacy/unit/test_umh_wave9_wrapper_removal.py` asserts:
1. `eos_ai/` directory does NOT exist
2. No `eos.` or `eos_ai.` imports remain anywhere in UMH

This test defines the completion criteria for the full migration.

## Appendix D: eos_ai/.env Migration Scope

256 references to `eos_ai/.env` across:
- Docker compose env_file entries (3)
- Shell scripts source/check (6)
- Python load_dotenv calls (~20)
- Claude Code skills/commands (12)
- Documentation/CLAUDE.md (10+)
- Test fixtures (5)

**Recommendation:** Consolidate to `${UMH_ROOT}/.env` (single root env file)
during R8h, or move to `umh_runtime/.env` as a direct rename.
