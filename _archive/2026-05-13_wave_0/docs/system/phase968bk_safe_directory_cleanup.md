# Phase 96.8BK — Safe Directory Cleanup and Compatibility Shims

> Generated: 2026-05-09
> Executor: Developer Agent (Claude Code)
> Baseline commit: 10b441ed702837b16d52971161faa9a3a82d6f95

---

## Executive Summary

Phase 96.8BK prepares the physical repo for staged migration by creating
canonical directories, building detailed migration plans for every major
package, generating a machine-readable scripts/tools diff index, and
establishing the compatibility shim pattern.

**No active runtime code was moved. No imports were changed. No services restarted.**

---

## Files Created

### Canonical Directories
| Directory | Purpose | README |
|-----------|---------|--------|
| `substrate/` | Canonical UMH substrate target | `substrate/README.md` |
| `interfaces/` | User-facing surfaces target | `interfaces/README.md` |
| `platforms/` | Product layers target | `platforms/README.md` |
| `tests/active/` | Active runtime tests | — |
| `tests/legacy/` | Legacy/dormant tests | — |
| `tests/legacy/umh/` | UMH-specific legacy tests | — |
| `tests/proofs/` | Proof validation tests | — |

### Compatibility Documentation
| File | Purpose |
|------|---------|
| `substrate/compatibility.md` | Shim pattern documentation |

### Migration Plans
| File | Purpose |
|------|---------|
| `docs/migrations/eos_ai_to_substrate_migration_plan.md` | 120+ modules, 5 priority tiers |
| `docs/migrations/core_to_substrate_migration_plan.md` | 238 files, 5 priority tiers |
| `docs/migrations/scripts_tools_cleanup_plan.md` | 234 files, 4 cleanup phases |
| `docs/migrations/test_suite_migration_plan.md` | 357 tests, 7 categories |
| `docs/migrations/umh_value_extraction_plan.md` | 870 files, 6 extraction categories |
| `docs/migrations/proof_report_engine_cleanup_plan.md` | 22 modules, 3 classifications |

### Data Artifacts
| File | Purpose |
|------|---------|
| `data/system/scripts_tools_diff_index.json` | 234 entries, hash-compared |

---

## Files Moved

| File | From | To | Reason |
|------|------|----|--------|
| `eos_backup_20260326.tar.gz` | `backups/` | `archive/stale_backups/` | Phase 96.8BJ |
| `discord_bot.py.bak.20260508` | `services/` | `archive/stale_backups/` | Phase 96.8BI |

Both moves were verified from prior phases. No new moves in this phase.

---

## Files Deleted

None. All cleanup is documented but deferred.

---

## Files Quarantined

None new. Prior quarantines verified in place.

---

## Shims Created

No Python import shims created. The shim pattern is documented in
`substrate/compatibility.md` for use during Stage 2 migration.

---

## Imports Tested

No imports changed — verification not needed.
Runtime import chain remains:
```
services/discord_bot.py → eos_ai.* (50+ modules)
handlers/substrate_command_handler.py → core.* (25+ modules)
```

---

## Runtime Risk Assessment

| Risk | Level | Mitigation |
|------|-------|------------|
| Discord bot disruption | ZERO | No code modified |
| Import chain breakage | ZERO | No imports changed |
| Handler functionality | ZERO | No handlers modified |
| Data loss | ZERO | No data files modified |

---

## Scripts/Tools Diff Summary

| Category | Count | Action |
|----------|-------|--------|
| Exact duplicates | 2 | DELETE_TOOLS_COPY (safe) |
| Near duplicates | 183 | REVIEW_DIFF (archive tools/ version) |
| Unique to scripts/ | 23 | KEEP |
| Unique to tools/ | 26 | MOVE_TO_SCRIPTS_CANDIDATE |
| **Total** | **234** | |

Root cause: multi-session drift. Different Claude Code sessions modified
files in different locations.

---

## Migration Plan Summary

### eos_ai/ → substrate/ (120+ modules)
- **Tier 1 (CRITICAL):** 13 modules — gateway, model_router, memory, db, etc.
- **Tier 2 (SUBSTRATE):** 8 modules — event_spine, transports, storage
- **Tier 3 (UTILITY):** 8 modules — scanner, embedder, primitives
- **Tier 4 (PLATFORM):** 12+ modules — platforms/eos, interfaces
- **Tier 5 (DORMANT):** 6+ modules — evolution_engine, trinity, etc.

### core/ → substrate/ (238 files)
- **Tier 1 (HANDLER-IMPORTED):** 31 modules — registry, control plane, workstation
- **Tier 2 (CANONICAL):** 12 modules — adapters, memory, ontology
- **Tier 3 (FOUNDATION):** 60+ modules — adapter engine, governance, execution
- **Tier 4 (TOOL MASTERY):** 36 modules — author, manager, research agents
- **Tier 5 (TOP-LEVEL):** 28 modules — misc utilities

### UMH Value Extraction (870 files)
- 6 extraction categories defined
- COMPARE_WITH_CURRENT: 5 subdirectories overlap with `core/`
- EXTRACT_PATTERNS: 8 subdirectories have reusable patterns
- EXTRACT_TO_SUBSTRATE: 3 subdirectories have useful contracts
- ARCHIVE: 5 subdirectories with no extractable value

### Report Engine Cleanup (22 modules)
- 12 REPORT_GENERATORS (misnamed as engines)
- 7 CANONICAL_SUBSTRATE (relay/transport)
- 3 OTHER (adapter gen, environment mapping, CU ingestion)
- Rename deferred to Stage 2 migration

---

## Remaining Cleanup (for future phases)

1. **Execute scripts/tools consolidation** — archive 183 near-duplicates, move 26 unique files
2. **Move tests to classified directories** — 357 files need relocation
3. **Extract UMH value** — review 870 files, extract useful patterns
4. **Begin Stage 2 substrate migration** — start with Tier 2/3 (low risk) modules
5. **Rename report generators** — change `*_engine_v1.py` → `*_report_generator_v1.py`

---

## Updated System Status

See `docs/system/current_system_status.md` — updated to reflect Phase 96.8BK completion.

---

## Next Phase

**96.8BL — CONNECT_GWS_SCANNER_TO_CANONICAL_SUBSTRATE_INGESTION**

With convergence documented and cleanup planned, the next phase can
safely connect the GWS scanner to batch ingestion through the canonical
pipeline, knowing exactly where everything lives and where it's going.
