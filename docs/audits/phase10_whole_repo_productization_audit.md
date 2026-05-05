# Whole Repository Productization — Final Audit Report

**Phase 10 — Controlled Liquidation**
**Date:** 2026-04-25
**Status:** Phase 10A + 10B COMPLETE — 10C pending

---

## 1. Current Root Classification Table

| Directory | Files | Size | Non-Cache Files | Status | Classification |
|-----------|-------|------|-----------------|--------|----------------|
| `_holding/` | 42,205 | 483 MB | ~12,000 | Archive/holding from prior restructure | **archive** |
| `core/` | 0 | ~4 KB | 0 | Empty shell (only `__pycache__/`) | **delete** |
| `docs/` | 4 | 172 KB | 4 | Audit/planning docs | **docs** |
| `external_services/` | 1 | ~4 KB | 1 (`__init__.py`) | Empty namespace stub | **delete** |
| `infra/` | 8 | 40 KB | 8 | Docker, provisioning, env templates | **infra** |
| `logs/` | 46 | 7.0 MB | 46 | Active runtime logs + signal dirs | **runtime-data** |
| `media/` | 0 | 8 KB | 0 | Empty placeholder (just `higgsfield/` dir) | **delete** |
| `orchestrator/` | 0 | 16 KB | 0 | Empty approval queue dirs | **delete** |
| `parsers/` | 0 | ~4 KB | 0 | Empty shell (only `__pycache__/`) | **delete** |
| `scripts/` | 233 | 4.3 MB | ~196 | Operational backbone — orchestration, knowledge, smoke tests | **tools** |
| `services/` | 59 | 1.6 MB | ~33 | Live production services (Discord, Telegram, webhooks) | **interfaces + platform** |
| `tests/` | 561 | 17 MB | ~249 | Full test suite | **tests** |
| `umh/` | 193 | 1.9 MB | ~97 | Universal Mind Harness — canonical substrate | **substrate** |
| `vault/` | 16 | 252 KB | 16 | Conversation memory (runtime data) | **runtime-data** |

**Top-level files:**

| File | Status | Classification |
|------|--------|----------------|
| `.dockerignore` | Active | **infra** (move to `infra/`) |
| `.gitignore` | Active | **root** (stays) |
| `CLAUDE.md` | Active | **root** (stays) |
| `CLAUDE.local.md` | Active | **root** (stays, gitignored) |

**Missing (must create):**

| File | Purpose |
|------|---------|
| `pyproject.toml` | Package definition for umh + eos platform |
| `README.md` | Repository overview |

---

## 2. Dependency Graph Summary

### Critical State: Half-Migrated Repository

The repo is in a **dangerous half-migrated state**:

- `eos_ai/` — **DELETED from disk**, still imported by 2,113 references
- `eos_ai/.env` — **DELETED from disk**, still referenced by docker-compose.yml (3 services)
- `core/` — exists but **contains zero Python files** (empty shell), 75 import references in scripts
- `parsers/` — exists but **contains zero Python files** (empty shell), 4 import references in scripts

**Docker containers are running on stale processes.** Any restart of os-monitor, os-scraper, or os-discord will crash due to:
1. Missing `eos_ai/` module imports
2. Missing `../eos_ai/.env` env_file reference

### Import Matrix (active code → target namespace)

| Source | → eos_ai | → umh | → core | → parsers | → services | → scripts |
|--------|----------|-------|--------|-----------|------------|-----------|
| services/ (19 py) | 234 | 89 | 0 | 0 | 5 (self) | 0 |
| scripts/ (171 py) | 487 | 51 | 75 | 4 | 0 | 0 |
| tests/ (248 py) | 1,392 | 724 | 15 | 0 | 0 | 0 |
| umh/ (96 py) | 3 (broken) | 123 (internal) | 0 | 0 | 0 | 0 |
| **Total** | **2,116** | **987** | **90** | **4** | **5** | **0** |

### Where eos_ai code actually lives now

The `eos_ai/` codebase (~453 Python files) was moved to `_holding/runtime_legacy/eos_ai/`.
It is NOT importable from there. Active services reference the original namespace.

### UMH Coupling (3 violations)

1. `umh/workstation/business.py:365-367` — hard imports `eos_ai.agent_runtime`, `eos_ai.execution_spine`, `eos_ai.context_builder` (will crash at call time)
2. `umh/storage/adapters/neon.py:33` — references `Path("/opt/OS/eos_ai/.env")` (file missing)
3. `umh/environments/system_context.py:56` — references `Path("/opt/OS/eos_ai/.env")` (file missing)

### Bridge Discovery (gracefully degraded)

5 UMH modules attempt lazy imports from `eos_ai.adapters.*`:
- `adapters/bridge.py` → `eos_ai.adapters.umh_storage` (returns None)
- `goals/interfaces.py` → `eos_ai.adapters.umh_goals` (returns None)
- `strategy/interfaces.py` → `eos_ai.adapters.umh_strategy` (returns None)
- `memory/storage.py` → `eos_ai.adapters.umh_storage` (returns None)
- `execution/interfaces.py` → `eos_ai.adapters.umh_execution` (returns None)

All fail silently and fall back to null implementations. UMH runs standalone.

---

## 3. Folder Decisions (A–H)

| Folder | Decision | Target | Rationale |
|--------|----------|--------|-----------|
| `_holding/` | **G** — Archive | `archive/` (rename) | 483 MB of legacy code, data artifacts, prior knowledge vault. Historical reference value. Not runtime. |
| `core/` | **H** — Delete | N/A | Zero files. Empty `__pycache__/` only. Real code is in `_holding/runtime_legacy/core/`. |
| `docs/` | **F** — Docs | `docs/` (stays) | Already correctly placed. 4 audit documents. |
| `external_services/` | **H** — Delete | N/A | Single empty `__init__.py`. No consumers. No value. |
| `infra/` | **E** — Infra | `infra/` (stays) | Already correctly placed. Docker + provisioning. |
| `logs/` | **runtime-data** | `logs/` (stays, gitignored) | Active runtime logs. Already gitignored. |
| `media/` | **H** — Delete | N/A | Zero files. Empty directory structure. |
| `orchestrator/` | **H** — Delete | N/A | Zero files. Empty `approvals/` directory structure. |
| `parsers/` | **H** — Delete | N/A | Zero files. Empty `__pycache__/` only. Real code is in `_holding/runtime_legacy/parsers/`. |
| `scripts/` | **D** — Tools | `tools/` (rename) | 171 Python scripts: orchestration, knowledge system, smoke tests, daily ops. Dev/ops utilities. |
| `services/` | **Split: B + C** | See below | Contains both interface code (Discord, Telegram) and platform orchestration (handlers, intent routing). |
| `tests/` | **stays** | `tests/` | Already correctly placed. Well-structured test suite. |
| `umh/` | **stays** | `umh/` | Canonical substrate. Architecturally clean. |
| `vault/` | **runtime-data** | `data/vault/` or gitignored | Conversation memory files. Runtime data, not code. |

### services/ Split Plan

| Current Path | Target | Classification |
|-------------|--------|----------------|
| `services/discord_bot.py` | `interfaces/discord/bot.py` | **interface** |
| `services/telegram_control.py` | `interfaces/telegram/bot.py` | **interface** |
| `services/calendly_webhook.py` | `interfaces/webhooks/calendly.py` | **interface** |
| `services/dm_monitor.py` | `interfaces/discord/dm_monitor.py` | **interface** |
| `services/handlers/` | `platforms/eos/handlers/` | **platform** |
| `services/apify_scraper.py` | `tools/apify_scraper.py` | **tools** |
| `services/overnight_scrape.py` | `tools/overnight_scrape.py` | **tools** |
| `services/cost_tracker.py` | `platforms/eos/trackers/cost.py` | **platform** |
| `services/kpi_tracker.py` | `platforms/eos/trackers/kpi.py` | **platform** |
| `services/icp_scorer.py` | `platforms/eos/scoring/icp.py` | **platform** |
| `services/heartbeat.py` | `tools/heartbeat.py` | **tools** |
| `services/local_bridge_server.py` | `tools/local_bridge_server.py` | **tools** |
| `services/local_bridge_client.py` | `tools/local_bridge_client.py` | **tools** |
| `services/higgsfield_webhook.py` | `interfaces/webhooks/higgsfield.py` | **interface** |
| `services/.env` | `infra/.env` or `services/.env` (stays, gitignored) | **infra** |
| `services/requirements.txt` | Root or `infra/requirements.txt` | **infra** |

---

## 4. UMH Extraction Candidates

UMH is already well-extracted. Remaining work:

### Must Fix (violations of standalone contract)

1. **`umh/workstation/business.py:365-367`** — Remove or replace `eos_ai` hard imports
   - Replace `TaskType` with a local enum or UMH-defined equivalent
   - Replace `run_via_umh` with `umh.run()`
   - Replace `ContextBuilder` with `umh.context.builder.ContextBuilder`

2. **`umh/storage/adapters/neon.py:33`** — Change env path from `eos_ai/.env` to `services/.env` or `infra/.env`

3. **`umh/environments/system_context.py:56`** — Same env path fix

### Should Clean (bridge discovery to dead code)

5 modules attempt lazy imports from `eos_ai.adapters.*`. These should either:
- Be removed (if no platform adapter will ever exist)
- Be updated to look for `platforms.eos.adapters.*` instead

### Extraction from _holding (if any intelligence lives there)

The 453-file `_holding/runtime_legacy/eos_ai/` may contain intelligence logic that belongs in UMH.
A targeted audit is needed — but given that UMH was explicitly extracted from this codebase across 9 waves,
the presumption is that all intelligence is already in UMH. The remaining eos_ai code should be:
- Platform orchestration → `platforms/eos/`
- Adapters that bridge UMH to services → `platforms/eos/adapters/`
- Dead code → stays in archive

---

## 5. EOS Platform Candidates

Create `platforms/eos/` containing:

| Source | Target | Purpose |
|--------|--------|---------|
| `services/handlers/intent_handler.py` | `platforms/eos/handlers/intent.py` | Intent routing (gateway dispatch) |
| `services/handlers/pipeline_handler.py` | `platforms/eos/handlers/pipeline.py` | CRM pipeline handling |
| `services/handlers/voice_handler.py` | `platforms/eos/handlers/voice.py` | Voice processing orchestration |
| `services/handlers/cc_command_handler.py` | `platforms/eos/handlers/cc_command.py` | Claude Code command routing |
| `services/cost_tracker.py` | `platforms/eos/trackers/cost.py` | Cost tracking |
| `services/kpi_tracker.py` | `platforms/eos/trackers/kpi.py` | KPI tracking |
| `services/icp_scorer.py` | `platforms/eos/scoring/icp.py` | ICP lead scoring |

**Platform adapters** (from `_holding/runtime_legacy/eos_ai/` if still needed):
- `eos_ai/adapters/umh_storage.py` → `platforms/eos/adapters/storage.py`
- `eos_ai/adapters/umh_goals.py` → `platforms/eos/adapters/goals.py`
- `eos_ai/adapters/umh_strategy.py` → `platforms/eos/adapters/strategy.py`
- `eos_ai/adapters/umh_execution.py` → `platforms/eos/adapters/execution.py`

---

## 6. Interface Layer Candidates

| Source | Target | Transport |
|--------|--------|-----------|
| `services/discord_bot.py` | `interfaces/discord/bot.py` | Discord (py-cord) |
| `services/dm_monitor.py` | `interfaces/discord/dm_monitor.py` | Discord DM monitoring |
| `services/telegram_control.py` | `interfaces/telegram/bot.py` | Telegram (python-telegram-bot) |
| `services/calendly_webhook.py` | `interfaces/webhooks/calendly.py` | HTTP webhook (Flask) |
| `services/higgsfield_webhook.py` | `interfaces/webhooks/higgsfield.py` | HTTP webhook (Flask) |

Each interface must:
- Accept raw input from transport
- Translate to `UMHInput`
- Call `umh.gateway.entry.translate_and_run()` or `platforms.eos.handlers`
- Format and return response via transport

---

## 7. Tools / Infra / Docs Mapping

### tools/ (rename of scripts/)

| Category | Files | Purpose |
|----------|-------|---------|
| Orchestration | `orchestrator.py`, `orchestrator_loop.py`, `orchestrator_status.py`, `control_plane_run.py`, `force_execution_loop.py` | Continuous execution loops |
| Knowledge | `query_graph.py`, `codebase_graph.py`, `build_palace.py`, `session_bootstrap.py`, `verify_knowledge_system.py` | Codebase knowledge system |
| Notion | `notion_tasks_sync.py`, `notion_seed.py`, `notion_cleanup.py`, `notion_setup.py` (8+ files) | Notion workspace sync |
| Smoke tests | 50+ `substrate_*_smoke_test.py` | Integration/smoke tests → consider moving to `tests/smoke/` |
| Daily ops | `morning_intel.py`, `midday_checkin.py`, `eod_sync.py`, `nightly_consolidation.py`, `weekly_review.py` | Scheduled operations |
| Tool mastery | `tool_mastery_author.py`, `tool_mastery_manager.py`, `tool_mastery_research_dispatcher.py` | Tool skill authoring |
| Workflow | `workflow_engine.py`, `action_system.py`, `decisions.py`, `deferred.py` | Action/workflow runtime |

### infra/

| File | Purpose | Status |
|------|---------|--------|
| `docker-compose.yml` | Service composition | NEEDS UPDATE (eos_ai/.env refs) |
| `Dockerfile` | Container build | Current |
| `.env.example` | Env template | Current |
| `install.sh` | VPS provisioning | Current |
| `setup.sh` | Initial setup | Current |
| `patch_pycord.py` | Pycord monkey-patch | Current |
| `.env.sessions` | Session env vars | Current |
| `.dockerignore` | Docker build exclusions | Current |

### docs/

| File | Purpose |
|------|---------|
| `audits/controlled_collapse_ledger.md` | Collapse tracking |
| `audits/phase5b_revised_whole_repo_alignment.md` | Alignment plan |
| `audits/global_umh_extraction_audit.md` | UMH extraction tracking |
| `audits/phase5_structural_collapse_plan.md` | Original collapse plan |
| `audits/phase10_whole_repo_productization_audit.md` | THIS DOCUMENT |

---

## 8. Archive Candidates

| Source | Reason | Value |
|--------|--------|-------|
| `_holding/runtime_legacy/` (2,153 files, 42 MB) | Full previous codebase (eos_ai, core, parsers, services, tests, scripts) | Reference for migration gaps |
| `_holding/eos_product/` (4,498 files, 92 MB) | SaaS product code, ventures, knowledge | Product reference |
| `_holding/knowledge_vault/` (4,941 files, 28 MB) | Obsidian vault, Wiki, Content | Knowledge reference |
| `_holding/claude_code_harnessing/` (384 files, 7.4 MB) | Skills, planning, PHILOSOPHY.md, ARCHITECTURE.md | Active reference (some files may need to return to root) |
| `_holding/infra_ops/` (81 files, 2 MB) | Playwright MCP, docs, config | Reference |
| `_holding/data_artifacts/` (30,148 files, 313 MB) | Bulk data, media, logs, backups | LOW value — consider deep-delete |

### Notable files in _holding that may need to return

- `_holding/claude_code_harnessing/PHILOSOPHY.md` — referenced by CLAUDE.md ("Before building anything read PHILOSOPHY.md")
- `_holding/claude_code_harnessing/ARCHITECTURE.md` — referenced by CLAUDE.md ("Read ARCHITECTURE.md before any significant build decision")
- `_holding/claude_code_harnessing/PROTOCOLS.md` — referenced by CLAUDE.md ("See PROTOCOLS.md for full 4-layer documentation")

These files are referenced by active instructions but live in `_holding/`. They need to either:
- Move back to root or `docs/`
- Or CLAUDE.md references need updating

---

## 9. Delete Candidates

| Target | Reason | Safety |
|--------|--------|--------|
| `core/` | Zero Python files. Only `__pycache__/`. | **SAFE** — no imports resolve (real code in `_holding/runtime_legacy/core/`) |
| `parsers/` | Zero Python files. Only `__pycache__/`. | **SAFE** — no imports resolve (real code in `_holding/runtime_legacy/parsers/`) |
| `external_services/` | Single empty `__init__.py`. No consumers. | **SAFE** — grep confirms zero imports |
| `media/` | Zero files. Empty `higgsfield/` dir. | **SAFE** — no references |
| `orchestrator/` | Zero files. Empty `approvals/` structure. | **SAFE** — the actual orchestrator code is `scripts/orchestrator.py` |
| `_holding/data_artifacts/` | 30K files, 313 MB of bulk data/media/logs/backups | **SAFE to deep-delete** — no code, no imports, runtime data only. Consider whether any backups have value first. |

---

## 10. Safe Moves (Wave 10A)

These moves have zero or trivial import rewrite requirements and no behavior change:

### Tier 1 — Zero Risk (no code, no imports)

| Action | Detail |
|--------|--------|
| Delete `core/` | Empty dir, only `__pycache__/` |
| Delete `parsers/` | Empty dir, only `__pycache__/` |
| Delete `external_services/` | Single empty `__init__.py` |
| Delete `media/` | Empty dirs |
| Delete `orchestrator/` | Empty dirs |
| Rename `_holding/` → `archive/` | Pure rename, no code references |
| Create `platforms/eos/` | New empty dir |
| Create `interfaces/` | New empty dir |
| Create `pyproject.toml` | New file |
| Create `README.md` | New file |

### Tier 2 — Low Risk (config-only changes)

| Action | Detail | Import Rewrite |
|--------|--------|----------------|
| Fix `infra/docker-compose.yml` | Remove `../eos_ai/.env` refs (3 services), point to `../services/.env` | None (config file) |
| Fix `umh/storage/adapters/neon.py` | Change env path from `eos_ai/.env` to `services/.env` | None (path string) |
| Fix `umh/environments/system_context.py` | Same env path fix | None (path string) |
| Fix `umh/workstation/business.py` | Remove 3 hard `eos_ai` imports | Replace with UMH equivalents |
| Update `.gitignore` | Add `archive/`, `data/`, update paths | None |
| Move `vault/` → `data/vault/` | Runtime conversation memory | None (no imports) |
| Move root `.dockerignore` → `infra/.dockerignore` | Cleaner root | None |

### Tier 3 — Medium Risk (code moves with import rewrites)

| Action | Detail | Impact |
|--------|--------|--------|
| Rename `scripts/` → `tools/` | 171 Python files move | Need to update any cron jobs, CI, docker-compose, CLAUDE.md references |
| Move `services/handlers/` → `platforms/eos/handlers/` | 4 handler files | Need to update `services/discord_bot.py` imports |
| Split `services/` into `interfaces/` | Move transport-layer services | Need to update docker-compose commands |

### Tier 4 — High Risk (deferred to Wave 10B)

| Action | Detail | Why Deferred |
|--------|--------|--------------|
| Resolve 2,116 `eos_ai` import references | services/ (234), scripts/ (487), tests/ (1,392) | Massive scope. Needs systematic approach: create `eos_ai` → `umh`/`platforms.eos` import compatibility layer first. |
| Resolve 90 `core` import references | scripts/ (75), tests/ (15) | Code is already in archive. Scripts that import core will break — need to decide: port to umh, or accept breakage. |
| Extract needed adapters from `_holding/runtime_legacy/eos_ai/` | Create `platforms/eos/adapters/` | Requires reading 453 files to find what's still needed |

---

## 11. Risk Analysis

### CRITICAL — Docker Restart Crash

**Impact:** All 4 running containers will crash on next restart
**Cause:** `eos_ai/` deleted, imports unresolved, env_file missing
**Mitigation (Tier 2):** Fix docker-compose.yml env_file paths immediately
**Mitigation (Tier 4):** Create eos_ai compatibility shim or port all imports

### HIGH — Half-Migrated State

**Impact:** Any new development on services/ or scripts/ hits import errors immediately
**Cause:** eos_ai namespace deleted without creating compatibility layer
**Options:**
1. **Shim approach** — Create `eos_ai/` as thin re-export layer that imports from `umh` and `platforms.eos`. Preserves all 2,116 import sites. Allows incremental migration.
2. **Mass rewrite** — Update all 2,116 import references. Riskier, but cleaner final state.
3. **Restore** — Move `_holding/runtime_legacy/eos_ai/` back to `eos_ai/`. Regression but stabilizes immediately.

**Recommendation:** Option 1 (shim) for stability, then incremental migration in Tier 4.

### MEDIUM — CLAUDE.md References to Moved Files

**Impact:** Developer Agent instructions reference files that no longer exist at documented paths
**Files:** PHILOSOPHY.md, ARCHITECTURE.md, PROTOCOLS.md (all in `_holding/claude_code_harnessing/`)
**Mitigation:** Move these to `docs/` and update CLAUDE.md references

### LOW — Smoke Tests in Wrong Location

**Impact:** 50+ substrate smoke tests in `scripts/` should be in `tests/smoke/`
**Mitigation:** Move as part of `scripts/` → `tools/` rename

---

## 12. Exact Next Execution Wave

### Wave 10A — Immediate Stabilization (execute now)

**Goal:** Stop the bleeding. Make Docker restarts safe. Clean dead directories.

```
Step 1: Delete empty directories
  - rm -rf core/ parsers/ external_services/ media/ orchestrator/

Step 2: Fix Docker env_file crash
  - Remove ../eos_ai/.env from docker-compose.yml (3 services)
  - Merge any needed vars from eos_ai/.env into services/.env

Step 3: Fix UMH env path references
  - umh/storage/adapters/neon.py — update .env path
  - umh/environments/system_context.py — update .env path

Step 4: Fix UMH standalone violations
  - umh/workstation/business.py — remove eos_ai imports

Step 5: Rename _holding/ → archive/
  - Pure rename, zero import impact

Step 6: Move referenced docs back
  - PHILOSOPHY.md, ARCHITECTURE.md, PROTOCOLS.md → docs/
  - Update CLAUDE.md references

Step 7: Create missing root files
  - pyproject.toml
  - README.md

Step 8: Update .gitignore
  - Add archive/, data/
  - Remove stale eos_ai references
```

### Wave 10B — Structural Moves (execute after 10A verified)

**Goal:** Establish target directory structure.

```
Step 1: Create target directories
  - platforms/eos/
  - interfaces/discord/
  - interfaces/telegram/
  - interfaces/webhooks/
  - tools/
  - data/

Step 2: Rename scripts/ → tools/
  - Update all cron jobs, CLAUDE.md, docker refs
  - Move smoke tests to tests/smoke/

Step 3: Move services/handlers/ → platforms/eos/handlers/
  - Update discord_bot.py imports

Step 4: Create eos_ai compatibility shim
  - eos_ai/__init__.py that re-exports from umh + platforms.eos
  - Preserves all 2,116 import sites
  - Enables incremental migration

Step 5: Move vault/ → data/vault/
```

### Wave 10C — Interface Extraction (execute after 10B verified)

**Goal:** Clean interface/platform separation.

```
Step 1: Move transport services to interfaces/
  - discord_bot.py → interfaces/discord/
  - telegram_control.py → interfaces/telegram/
  - webhooks → interfaces/webhooks/
  - Update docker-compose.yml commands

Step 2: Move platform services to platforms/eos/
  - trackers, scorers → platforms/eos/

Step 3: Update docker-compose.yml for new paths

Step 4: Full test suite pass
```

### Wave 10D — Import Migration (execute after 10C verified)

**Goal:** Eliminate eos_ai compatibility shim.

```
Step 1: Migrate services/ imports (234) — eos_ai → umh/platforms.eos
Step 2: Migrate scripts/ imports (487) — same
Step 3: Migrate tests/ imports (1,392) — same
Step 4: Remove eos_ai compatibility shim
Step 5: Remove core/ import references (90) — port or remove
Step 6: Final test suite pass
Step 7: Production verification
```

---

## Post-Productization Target State

```
/opt/OS/
├── umh/                          # Canonical substrate (96 modules)
├── platforms/
│   └── eos/                      # EOS platform (handlers, trackers, adapters)
├── interfaces/
│   ├── discord/                  # Discord bot + DM monitor
│   ├── telegram/                 # Telegram bot
│   └── webhooks/                 # Calendly, Higgsfield webhooks
├── tools/                        # Scripts, orchestration, knowledge system
├── infra/                        # Docker, provisioning, env templates
├── docs/                         # Architecture, audits, philosophy
│   └── audits/                   # Phase audit documents
├── tests/                        # All tests
│   ├── unit/                     # UMH unit tests
│   ├── substrate/                # Substrate integration tests
│   ├── platforms/eos/            # Platform tests
│   ├── adapters/                 # Adapter tests
│   ├── runtime/                  # Runtime tests
│   └── smoke/                    # Smoke tests (from scripts/)
├── data/                         # Runtime data (gitignored)
│   └── vault/                    # Conversation memory
├── logs/                         # Runtime logs (gitignored)
├── archive/                      # Historical reference (from _holding/)
├── .claude/                      # Claude Code config
├── pyproject.toml                # Package definition
├── README.md                     # Repository overview
├── CLAUDE.md                     # Developer Agent soul document
└── .gitignore                    # Updated for new structure
```

Zero ambiguous folders. Zero legacy shadow systems. UMH as single intelligence substrate. EOS as clean platform layer. Clean, installable, scalable.

---

*This is the authoritative plan. Execution begins with Wave 10A upon approval.*
